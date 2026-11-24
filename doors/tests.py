import io
import os
import tempfile

from unittest.mock import patch

from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse

from PIL import Image

from .models import Door, DoorPreview


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
