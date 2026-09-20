import io
import tempfile
from pathlib import Path
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from .models import ImageAsset, SiteChrome

ADMIN_SECRET = 'arch-test-admin-secret'
OTHER_SECRET = 'hobbies-admin-secret'


def _png_bytes(width=8, height=6, color='red'):
    buf = io.BytesIO()
    Image.new('RGB', (width, height), color=color).save(buf, format='PNG')
    return buf.getvalue()


def _upload(name='hero.png', width=8, height=6, content_type='image/png'):
    return SimpleUploadedFile(name, _png_bytes(width, height), content_type=content_type)


@override_settings(
    ARCH_ADMIN_SECRET=ADMIN_SECRET,
    ADMIN_SECRET_KEY=OTHER_SECRET,
    MEDIA_ROOT=tempfile.mkdtemp(),
    MEDIA_URL='/media/',
    SERVE_MEDIA=True,
    DEBUG=True,
)
class ArchMediaAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _auth(self, key=ADMIN_SECRET):
        return {'HTTP_X_ADMIN_KEY': key}

    def test_health_still_ok(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_existing_order_routes_still_resolve(self):
        self.assertEqual(reverse('orders'), '/api/orders/')
        self.assertEqual(reverse('woo-webhook'), '/api/woo/webhook/')
        self.assertEqual(reverse('payment-status'), '/api/payment/status/')

    def test_list_empty(self):
        response = self.client.get('/api/arch/images/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'count': 0, 'results': []})

    def test_upload_requires_admin_key(self):
        response = self.client.post(
            '/api/arch/images/',
            {'file': _upload()},
            format='multipart',
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(ImageAsset.objects.count(), 0)

    def test_upload_accepts_arch_admin_secret(self):
        response = self.client.post(
            '/api/arch/images/',
            {'file': _upload(), 'alt': 'Courtyard', 'slot': 'hero', 'title': 'Nairobi courtyard'},
            format='multipart',
            **self._auth(ADMIN_SECRET),
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body['alt'], 'Courtyard')
        self.assertEqual(body['slot'], 'hero')
        self.assertEqual(body['title'], 'Nairobi courtyard')
        self.assertEqual(body['content_type'], 'image/png')
        self.assertEqual(body['width'], 8)
        self.assertEqual(body['height'], 6)
        self.assertEqual(body['site'], 'arch')
        self.assertTrue(body['storage_key'].startswith('arch/arch/'))
        self.assertIn('/media/', body['url'])
        asset = ImageAsset.objects.get(pk=body['id'])
        self.assertTrue(asset.file)
        stored = Path(asset.file.path)
        self.assertTrue(stored.exists())
        self.assertGreater(stored.stat().st_size, 0)
        self.assertEqual(ImageAsset._meta.get_field('file').get_internal_type(), 'FileField')
        media = self.client.get(body['url'].split('http://testserver')[-1])
        self.assertEqual(media.status_code, 200)
        payload = b''.join(media.streaming_content)
        self.assertGreater(len(payload), 0)
        self.assertEqual(payload[:8], b'\x89PNG\r\n\x1a\n')

    def test_upload_accepts_admin_secret_key_fallback(self):
        response = self.client.post(
            '/api/arch/images/',
            {'file': _upload()},
            format='multipart',
            **self._auth(OTHER_SECRET),
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_upload_rejects_non_image(self):
        upload = SimpleUploadedFile('notes.txt', b'hello', content_type='text/plain')
        response = self.client.post(
            '/api/arch/images/',
            {'file': upload},
            format='multipart',
            **self._auth(),
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_alt_sort_slot(self):
        created = self.client.post(
            '/api/arch/images/',
            {'file': _upload(), 'alt': 'old'},
            format='multipart',
            **self._auth(),
        ).json()
        response = self.client.patch(
            f"/api/arch/images/{created['id']}/",
            {'alt': 'new alt', 'sort_order': 4, 'slot': 'gallery'},
            format='json',
            **self._auth(),
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['alt'], 'new alt')
        self.assertEqual(body['sort_order'], 4)
        self.assertEqual(body['slot'], 'gallery')

    def test_patch_requires_admin(self):
        created = self.client.post(
            '/api/arch/images/',
            {'file': _upload()},
            format='multipart',
            **self._auth(),
        ).json()
        response = self.client.patch(
            f"/api/arch/images/{created['id']}/",
            {'alt': 'nope'},
            format='json',
        )
        self.assertEqual(response.status_code, 401)

    def test_delete_removes_file(self):
        created = self.client.post(
            '/api/arch/images/',
            {'file': _upload()},
            format='multipart',
            **self._auth(),
        ).json()
        asset = ImageAsset.objects.get(pk=created['id'])
        path = Path(asset.file.path)
        self.assertTrue(path.exists())
        response = self.client.delete(f"/api/arch/images/{created['id']}/", **self._auth())
        self.assertEqual(response.status_code, 204)
        self.assertFalse(ImageAsset.objects.filter(pk=created['id']).exists())
        self.assertFalse(path.exists())

    def test_reorder(self):
        a = self.client.post(
            '/api/arch/images/',
            {'file': _upload('a.png'), 'slot': 'a'},
            format='multipart',
            **self._auth(),
        ).json()
        b = self.client.post(
            '/api/arch/images/',
            {'file': _upload('b.png'), 'slot': 'b'},
            format='multipart',
            **self._auth(),
        ).json()
        response = self.client.put(
            '/api/arch/images/reorder/',
            [
                {'id': a['id'], 'sort_order': 2, 'slot': 'footer'},
                {'id': b['id'], 'sort_order': 1},
            ],
            format='json',
            **self._auth(),
        )
        self.assertEqual(response.status_code, 200, response.content)
        listed = self.client.get('/api/arch/images/').json()['results']
        self.assertEqual([item['id'] for item in listed], [b['id'], a['id']])
        self.assertEqual(ImageAsset.objects.get(pk=a['id']).slot, 'footer')
        self.assertEqual(ImageAsset.objects.get(pk=b['id']).slot, 'b')

    def test_chrome_get_empty_then_put(self):
        response = self.client.get('/api/arch/chrome/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['site'], 'arch')
        self.assertEqual(response.json()['chrome'], {})

        denied = self.client.put('/api/arch/chrome/', {'nav': {'label': 'Work'}}, format='json')
        self.assertEqual(denied.status_code, 401)

        updated = self.client.put(
            '/api/arch/chrome/',
            {'nav': {'label': 'Work'}, 'theme': 'dark'},
            format='json',
            **self._auth(),
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['chrome']['nav']['label'], 'Work')
        self.assertEqual(SiteChrome.objects.get(site='arch').data['theme'], 'dark')

        wrapped = self.client.put(
            '/api/arch/chrome/',
            {'chrome': {'footer': '© Arch'}},
            format='json',
            **self._auth(),
        )
        self.assertEqual(wrapped.status_code, 200)
        self.assertEqual(wrapped.json()['chrome'], {'footer': '© Arch'})

    def test_bytes_not_written_to_postgres_fields(self):
        field_types = {f.name: f.get_internal_type() for f in ImageAsset._meta.get_fields() if hasattr(f, 'get_internal_type')}
        self.assertEqual(field_types['file'], 'FileField')
        self.assertNotIn('BinaryField', field_types.values())
