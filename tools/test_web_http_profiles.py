"""Named request profiles bind the applied HTTP headers without changing network authority."""
from unittest.mock import Mock, patch
import unittest

from loop_engine.core import web_fetch


class HttpProfiles(unittest.TestCase):
    def profile(self, **changes):
        return web_fetch.WebHttpClientProfile(**{**dict(profile_id='research-desktop', revision='1.0.0',
            user_agent='Baltor-compatibility-test/1', accept_language='en-US,en;q=0.8'), **changes})

    def test_profile_is_exact_and_immutable_by_digest(self):
        record = self.profile().to_record()
        self.assertEqual(web_fetch.WebHttpClientProfile.from_record(record), self.profile())
        for changed in ({**record, 'user_agent': 'Different/1'}, {**record, 'authorization': 'unused'},
                        {**record, 'record_type': 'web_http_client_profile/v0'}):
            with self.assertRaises(web_fetch.WebFetchError):
                web_fetch.WebHttpClientProfile.from_record(changed)

    def test_headers_cannot_inject_another_header_or_carry_a_credential_assignment(self):
        for value in ('reader\r\nX-Unexpected: value', 'reader\x00', 'Bearer synthetic-value', 'token=synthetic-value'):
            with self.assertRaises(web_fetch.WebFetchError):
                self.profile(user_agent=value)

    def test_selected_profile_reaches_the_transport(self):
        opener = Mock()
        with patch.object(web_fetch.urllib.request, 'build_opener', return_value=opener):
            web_fetch._open_without_redirects('https://example.com/data', 4, self.profile())
        request = opener.open.call_args.args[0]
        headers = {key.lower(): value for key, value in request.header_items()}
        self.assertEqual(headers['user-agent'], self.profile().user_agent)
        self.assertEqual(headers['accept-language'], self.profile().accept_language)
        self.assertNotIn('authorization', headers)

    def test_profile_change_changes_the_approved_effect(self):
        with patch.object(web_fetch, '_validate_public_https'):
            first = web_fetch.WebFetchRequest('https://example.com/data', 'Compare clients', client_profile=self.profile())
            second = web_fetch.WebFetchRequest('https://example.com/data', 'Compare clients',
                                              client_profile=self.profile(user_agent='Another-reader/2'))
        self.assertNotEqual(web_fetch._effect(first), web_fetch._effect(second))
        self.assertEqual(first.url, second.url)

    def test_profile_never_makes_a_private_destination_eligible(self):
        with self.assertRaises(web_fetch.WebFetchError):
            web_fetch.WebFetchRequest('https://127.0.0.1/data', 'Invalid destination', client_profile=self.profile())

    def test_profile_is_preserved_across_a_validated_redirect(self):
        from email.message import Message
        headers = Message()
        headers['Location'] = 'https://example.com/final'
        redirect = web_fetch.urllib.error.HTTPError('https://example.com/start', 302, 'Found', headers, None)
        with patch.object(web_fetch, '_validate_public_https'), patch.object(
                web_fetch, '_open_without_redirects', side_effect=[redirect, Mock()]) as opened:
            request = web_fetch.WebFetchRequest('https://example.com/start', 'Compare clients', client_profile=self.profile())
            _, _, hops = web_fetch._fetch_with_validated_hops(request)
        self.assertEqual(len(hops), 2)
        self.assertTrue(all(call.args[2] == self.profile() for call in opened.call_args_list))


if __name__ == '__main__':
    unittest.main()
