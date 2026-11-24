import io
import os
import tempfile
import types

from unittest.mock import patch

import numpy as np
from PIL import Image

from django.contrib.messages import get_messages
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Door, DoorPreview
from .views import _read_image_from_storage, process_door_preview


def make_image(fmt='JPEG', name='photo.jpg', pad=0):
    buf = io.BytesIO()
    Image.new('RGB', (100, 100), 'red').save(buf, fmt)

    return SimpleUploadedFile(
        name,
        buf.getvalue() + b'\0' * pad,
    )


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class PreviewValidationTests(TestCase):

    def setUp(self):
        door_image = make_image('JPEG', 'door.jpg')
        self.door = Door.objects.create(
            name='Test door',
            category='bedroom',
            material='hard_wood',
            description='Test description',
            height='78',
            width='36',
            thickness='32',
            finish_type='matte',
            image_main=door_image,
        )
        self.addCleanup(self.door.image_main.delete, save=False)

    def post(self, image=None, **overrides):
        data = {
            'door_id': str(self.door.pk),
            'rect_x': '10',
            'rect_y': '10',
            'rect_w': '30',
            'rect_h': '60',
        }

        data.update(overrides)
        data['house_image'] = image or make_image()

        def test_render(request, template_name, context):
            response = HttpResponse(status=200)

            # Capture messages without invoking Django template rendering.
            messages_list = list(get_messages(request))
            response._test_messages = messages_list
            response.context = {'messages': messages_list}

            return response

        with patch('doors.views.render', side_effect=test_render):
            return self.client.post(reverse('ai_preview'), data)

    def assertRejected(self, response, text):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(DoorPreview.objects.count(), 0)

        stored_messages = getattr(response, '_test_messages', None)
        if stored_messages is None and getattr(response, 'context', None):
            stored_messages = response.context.get('messages', [])
        if stored_messages is None:
            stored_messages = list(get_messages(response.wsgi_request))

        messages_list = [str(message) for message in stored_messages]

        self.assertTrue(
            any(text in message for message in messages_list),
            messages_list,
        )

    def test_non_image_file_rejected(self):
        bad = SimpleUploadedFile(
            'evil.html',
            b'<script>x</script>',
        )

        self.assertRejected(
            self.post(image=bad),
            'valid JPG, PNG or WebP',
        )

    def test_gif_rejected(self):
        self.assertRejected(
            self.post(image=make_image('GIF', 'a.gif')),
            'Only JPG, PNG or WebP',
        )

    def test_oversized_file_rejected(self):
        big = make_image(pad=11 * 1024 * 1024)

        self.assertRejected(
            self.post(image=big),
            'too large',
        )

    def test_non_numeric_door_id_is_not_a_500(self):
        self.assertRejected(
            self.post(door_id='abc'),
            'does not exist',
        )

    def test_unknown_door_id_rejected(self):
        self.assertRejected(
            self.post(door_id='99999'),
            'does not exist',
        )

    def test_nan_rectangle_rejected(self):
        self.assertRejected(
            self.post(rect_x='nan'),
            'Enter a number',
        )

    def test_rectangle_outside_photo_rejected(self):
        self.assertRejected(
            self.post(rect_x='90', rect_w='30'),
            'inside the photo',
        )

    def test_failed_processing_leaves_no_rows_or_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                with patch('doors.views.process_door_preview', return_value=None):
                    response = self.post()

                self.assertRejected(
                    response,
                    'Preview generation failed',
                )

                house_dir = os.path.join(
                    tmp,
                    'previews',
                    'house',
                )

                self.assertEqual(
                    os.listdir(house_dir)
                    if os.path.isdir(house_dir)
                    else [],
                    [],
                )

    def test_result_file_removed_if_saving_row_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):

                result_dir = os.path.join(
                    tmp,
                    'previews',
                    'result',
                )

                os.makedirs(result_dir)

                result_file = os.path.join(result_dir, 'x.jpg')

                with open(result_file, 'wb') as fh:
                    fh.write(b'x')

                real_save = DoorPreview.save
                calls = {'n': 0}

                def flaky_save(instance, *args, **kwargs):
                    calls['n'] += 1

                    if calls['n'] == 2:
                        raise RuntimeError('db down')

                    return real_save(instance, *args, **kwargs)

                with patch(
                    'doors.views.process_door_preview',
                    return_value='previews/result/x.jpg',
                ), patch.object(
                    DoorPreview,
                    'save',
                    flaky_save,
                ):
                    self.post()

                self.assertEqual(
                    DoorPreview.objects.count(),
                    0,
                )

                self.assertFalse(
                    os.path.exists(result_file),
                )


class NoPathStorage:
    """Storage wrapper that deliberately does not implement path()."""

    def __init__(self, location=None, base_url=None):
        self._fs = FileSystemStorage(location=location, base_url=base_url)

    def open(self, name, mode='rb'):
        return self._fs.open(name, mode)

    def save(self, name, content, max_length=None):
        return self._fs.save(name, content, max_length=max_length)

    def delete(self, name):
        return self._fs.delete(name)

    def exists(self, name):
        return self._fs.exists(name)

    def url(self, name):
        return self._fs.url(name)

    def generate_filename(self, filename):
        return self._fs.generate_filename(filename)

    def get_available_name(self, name, max_length=None):
        return self._fs.get_available_name(name, max_length=max_length)


class StorageReadHelperTests(TestCase):
    def _save_image(self, storage, path, fmt='JPEG', name='image.jpg'):
        return storage.save(path, make_image(fmt=fmt, name=name))

    def test_successful_image_loading_through_django_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = FileSystemStorage(location=tmp)
            saved_name = self._save_image(storage, 'doors/test.jpg')

            image_file = types.SimpleNamespace(name=saved_name, storage=storage)
            image = _read_image_from_storage(image_file)

            self.assertIsNotNone(image)
            self.assertEqual(image.shape[:2], (100, 100))

    def test_storage_reader_handles_short_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = FileSystemStorage(location=tmp)
            saved_name = self._save_image(storage, 'doors/shortreads.jpg')

            real_open = storage.open

            class ShortReadFile:
                def __init__(self, file_obj, chunk_size=10):
                    self._file = file_obj
                    self._chunk_size = chunk_size

                def read(self, size=-1):
                    if size is None or size < 0:
                        return self._file.read()
                    return self._file.read(min(size, self._chunk_size))

                def __enter__(self):
                    self._file.__enter__()
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return self._file.__exit__(exc_type, exc, tb)

            def open_short_reads(name, mode='rb'):
                return ShortReadFile(real_open(name, mode))

            with patch.object(storage, 'open', side_effect=open_short_reads):
                image_file = types.SimpleNamespace(name=saved_name, storage=storage)
                image = _read_image_from_storage(image_file)

            self.assertIsNotNone(image)
            self.assertEqual(image.shape[:2], (100, 100))

    def test_storage_backend_without_path_support(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = NoPathStorage(location=tmp)
            self.assertFalse(hasattr(storage, 'path'))

            saved_name = self._save_image(storage, 'doors/nopath.jpg')
            image_file = types.SimpleNamespace(name=saved_name, storage=storage)

            image = _read_image_from_storage(image_file)

            self.assertIsNotNone(image)
            self.assertEqual(image.shape[:2], (100, 100))

    def test_missing_image_returns_none(self):
        self.assertIsNone(_read_image_from_storage(None))
        self.assertIsNone(_read_image_from_storage(types.SimpleNamespace(name='', storage=None)))

        with tempfile.TemporaryDirectory() as tmp:
            storage = FileSystemStorage(location=tmp)
            image_file = types.SimpleNamespace(name='doors/missing.jpg', storage=storage)
            self.assertIsNone(_read_image_from_storage(image_file))

    def test_corrupted_image_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = FileSystemStorage(location=tmp)
            saved_name = storage.save('doors/corrupt.jpg', ContentFile(b'not-an-image'))
            image_file = types.SimpleNamespace(name=saved_name, storage=storage)

            self.assertIsNone(_read_image_from_storage(image_file))

    def test_image_exceeding_pixel_limit_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = FileSystemStorage(location=tmp)
            saved_name = self._save_image(storage, 'doors/large.jpg')
            image_file = types.SimpleNamespace(name=saved_name, storage=storage)

            huge = np.zeros((7000, 6000, 3), dtype=np.uint8)
            with patch('cv2.imdecode', return_value=huge):
                self.assertIsNone(_read_image_from_storage(image_file))

    def test_oversized_dimensions_rejected_before_opencv_decoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = FileSystemStorage(location=tmp)
            saved_name = self._save_image(storage, 'doors/huge-meta.jpg')
            image_file = types.SimpleNamespace(name=saved_name, storage=storage)

            class FakeImageCtx:
                def __init__(self, size):
                    self.size = size

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

            with patch('PIL.Image.open', return_value=FakeImageCtx((7000, 6000))), \
                 patch('cv2.imdecode') as mock_imdecode:
                result = _read_image_from_storage(image_file)

            self.assertIsNone(result)
            mock_imdecode.assert_not_called()

    def test_excessive_image_width_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = FileSystemStorage(location=tmp)
            saved_name = self._save_image(storage, 'doors/wide.jpg')
            image_file = types.SimpleNamespace(name=saved_name, storage=storage)

            class FakeImageCtx:
                def __init__(self, size):
                    self.size = size

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

            with patch('PIL.Image.open', return_value=FakeImageCtx((12001, 100))), \
                 patch('cv2.imdecode') as mock_imdecode:
                result = _read_image_from_storage(image_file)

            self.assertIsNone(result)
            mock_imdecode.assert_not_called()

    def test_excessive_image_height_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = FileSystemStorage(location=tmp)
            saved_name = self._save_image(storage, 'doors/tall.jpg')
            image_file = types.SimpleNamespace(name=saved_name, storage=storage)

            class FakeImageCtx:
                def __init__(self, size):
                    self.size = size

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

            with patch('PIL.Image.open', return_value=FakeImageCtx((100, 12001))), \
                 patch('cv2.imdecode') as mock_imdecode:
                result = _read_image_from_storage(image_file)

            self.assertIsNone(result)
            mock_imdecode.assert_not_called()

    def test_house_image_processing_stays_within_configured_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = FileSystemStorage(location=tmp)
            buf = io.BytesIO()
            Image.new('RGB', (3000, 3000), 'white').save(buf, 'JPEG')
            saved_name = storage.save('doors/big-house.jpg', ContentFile(buf.getvalue()))
            image_file = types.SimpleNamespace(name=saved_name, storage=storage)

            image = _read_image_from_storage(image_file)

            self.assertIsNotNone(image)
            self.assertLessEqual(image.shape[0] * image.shape[1], 8_000_000)


class PreviewProcessingTests(TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.override = override_settings(MEDIA_ROOT=self._tmp.name)
        self.override.enable()
        self.addCleanup(self.override.disable)

        self.door = Door.objects.create(
            name='Test door',
            category='bedroom',
            material='hard_wood',
            description='Test description',
            height='78',
            width='36',
            thickness='32',
            finish_type='matte',
            image_main=make_image('JPEG', 'door.jpg'),
        )
        self.addCleanup(self.door.image_main.delete, save=False)

    def _create_preview(self, house_file=None):
        preview = DoorPreview.objects.create(
            door=self.door,
            house_image=house_file or make_image('JPEG', 'house.jpg'),
        )
        self.addCleanup(preview.house_image.delete, save=False)
        return preview

    def _rect(self):
        return {'x': 10.0, 'y': 10.0, 'w': 30.0, 'h': 60.0}

    def test_process_door_preview_with_storage_backend_without_path_support(self):
        preview = self._create_preview()
        storage = NoPathStorage(location=self._tmp.name)

        preview.house_image.storage = storage
        preview.door.image_main.storage = storage
        preview.preview_image.storage = storage
        self.assertFalse(hasattr(storage, 'path'))

        result = process_door_preview(preview, self._rect())

        self.assertIsNotNone(result)
        self.assertTrue(storage.exists(result))
        self.assertTrue(result.startswith('previews/result/preview_'))
        storage.delete(result)

    def test_successful_preview_generation(self):
        preview = self._create_preview()

        result = process_door_preview(preview, self._rect())

        self.assertIsNotNone(result)
        self.assertTrue(preview.preview_image.storage.exists(result))
        self.assertTrue(result.startswith('previews/result/'))

        with preview.preview_image.storage.open(result, 'rb') as fh:
            data = fh.read()
        self.assertTrue(data.startswith(b'\xff\xd8'))

        preview.preview_image.storage.delete(result)

    def test_opencv_encoding_failure_returns_none(self):
        preview = self._create_preview()

        with patch('cv2.imencode', return_value=(False, None)):
            result = process_door_preview(preview, self._rect())

        self.assertIsNone(result)
        self.assertFalse(DoorPreview.objects.filter(pk=preview.pk).exclude(preview_image='').exists())

    def test_storage_write_failure_returns_none_and_leaves_no_generated_file(self):
        preview = self._create_preview()
        storage = preview.preview_image.storage

        with patch.object(storage, 'save', side_effect=RuntimeError('storage down')):
            result = process_door_preview(preview, self._rect())

        self.assertIsNone(result)
        result_dir = os.path.join(self._tmp.name, 'previews', 'result')
        self.assertEqual(
            os.listdir(result_dir) if os.path.isdir(result_dir) else [],
            [],
        )

    def test_failed_write_with_empty_saved_name_returns_none(self):
        preview = self._create_preview()
        storage = preview.preview_image.storage

        with patch.object(storage, 'save', return_value=''):
            result = process_door_preview(preview, self._rect())

        self.assertIsNone(result)
        result_dir = os.path.join(self._tmp.name, 'previews', 'result')
        self.assertEqual(
            os.listdir(result_dir) if os.path.isdir(result_dir) else [],
            [],
        )

    def test_oversized_existing_door_image_rejected(self):
        preview = self._create_preview()

        class FakeImageCtx:
            def __init__(self, size):
                self.size = size

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        real_open = Image.open

        def image_open_side_effect(*args, **kwargs):
            # First read is house image, second is existing door image.
            image_open_side_effect.calls += 1
            if image_open_side_effect.calls == 2:
                return FakeImageCtx((7000, 6000))
            return real_open(*args, **kwargs)

        image_open_side_effect.calls = 0

        with patch('PIL.Image.open', side_effect=image_open_side_effect):
            result = process_door_preview(preview, self._rect())

        self.assertIsNone(result)

    def test_door_background_removal_receives_bounded_image(self):
        from PIL import ImageDraw

        img = Image.new('RGB', (3200, 3200), 'white')
        draw = ImageDraw.Draw(img)
        draw.rectangle([600, 200, 2600, 3000], fill='red')
        buf = io.BytesIO()
        img.save(buf, 'JPEG')

        big_door = SimpleUploadedFile('big-door.jpg', buf.getvalue(), content_type='image/jpeg')
        self.door.image_main.save('big-door.jpg', big_door, save=True)
        preview = self._create_preview()

        captured = {}
        from doors.views import remove_white_background as real_remove

        def capture_bg(image):
            captured['pixels'] = image.shape[0] * image.shape[1]
            return real_remove(image)

        with patch('doors.views.remove_white_background', side_effect=capture_bg):
            result = process_door_preview(preview, self._rect())

        self.assertIsNotNone(result)
        self.assertIn('pixels', captured)
        self.assertLessEqual(captured['pixels'], 8_000_000)
        preview.preview_image.storage.delete(result)

    def test_partial_storage_write_triggers_cleanup(self):
        """Simulate a local partial write at the candidate path and verify cleanup.

        This does not prove partial-write behavior for remote storage backends.
        """
        preview = self._create_preview()
        storage = preview.preview_image.storage

        def save_then_fail(name, content, max_length=None):
            full_path = storage.path(name)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            data = content.read()
            with open(full_path, 'wb') as fh:
                fh.write(data)
            raise RuntimeError('partial write failure')

        with patch.object(storage, 'save', side_effect=save_then_fail):
            result = process_door_preview(preview, self._rect())

        self.assertIsNone(result)
        result_dir = os.path.join(self._tmp.name, 'previews', 'result')
        self.assertEqual(
            os.listdir(result_dir) if os.path.isdir(result_dir) else [],
            [],
        )

    def test_successful_preview_retains_valid_jpeg_output(self):
        preview = self._create_preview()

        result = process_door_preview(preview, self._rect())

        self.assertIsNotNone(result)
        self.assertTrue(preview.preview_image.storage.exists(result))
        with preview.preview_image.storage.open(result, 'rb') as fh:
            data = fh.read()
        self.assertTrue(data.startswith(b'\xff\xd8'))
        self.assertTrue(data.endswith(b'\xff\xd9'))
        preview.preview_image.storage.delete(result)
