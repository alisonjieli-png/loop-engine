"""Refusal and normalization checks for the authenticated community source."""
import json
import unittest

from knowledge_radar.community_intake import read_registry
from knowledge_radar.rapidapi_reddit import HOST, RapidApiRedditReader, RedditRequest, parse_posts


def post(**changes):
    value={"title":"Blender MCP animation workflow", "subreddit":"DesignAndAI",
           "permalink":"/r/DesignAndAI/comments/example/blender_workflow/", "created_utc":1790791200,
           "selftext":"A rigging workflow with export tests. https://github.com/example/rig",
           "url":"https://www.reddit.com/r/DesignAndAI/comments/example/blender_workflow/",
           "author":"not_retained", "author_fullname":"not_retained"}
    value.update(changes)
    return {"kind":"t3","data":value}


def body(*posts):
    return json.dumps({"success":True,"data":{"posts":list(posts)}}).encode()


class SourceChecks(unittest.TestCase):
    def test_complete_window_is_counted_without_a_silent_file_count_cutoff(self):
        rows=[post(permalink=f"/r/DesignAndAI/comments/p{i}/workflow/") for i in range(79)]
        leads,counts=parse_posts(body(*rows),RedditRequest("DesignAndAI"),read_registry())
        self.assertEqual(len(leads),79)
        self.assertEqual(counts["posts_considered"],79)
        self.assertNotIn("not_retained",json.dumps([lead.to_dict() for lead in leads]))
        self.assertTrue(all(lead.to_dict()["component_approved"] is False for lead in leads))

    def test_urls_and_community_identity_are_bound_to_the_request(self):
        leads,counts=parse_posts(body(post(permalink="https://attacker.example/redirect"),post(subreddit="other")),
                                 RedditRequest("DesignAndAI"),read_registry())
        self.assertEqual(leads,())
        self.assertEqual(counts["refused"],2)

    def test_duplicates_removed_posts_and_unclassified_posts_remain_visible(self):
        leads,counts=parse_posts(body(post(),post(),post(permalink="/r/DesignAndAI/comments/gone/x/",selftext="[removed]"),
            post(permalink="/r/DesignAndAI/comments/none/x/",title="Hello",selftext="",url="")),RedditRequest("DesignAndAI"),read_registry())
        self.assertEqual(len(leads),1)
        self.assertEqual((counts["duplicate_posts"],counts["refused"],counts["without_signal_hints"]),(1,1,1))

    def test_failed_or_changed_response_is_not_an_empty_success(self):
        for content in (b'{}',b'{"success":false,"data":{"posts":[]}}',b'<html>error</html>'):
            with self.assertRaises(ValueError):parse_posts(content,RedditRequest("DesignAndAI"),read_registry())
        with self.assertRaisesRegex(ValueError,"too_large"):
            parse_posts(body(post()),RedditRequest("DesignAndAI",maximum_bytes=10),read_registry())

    def test_credential_goes_only_to_the_fixed_host_without_redirects_or_retries(self):
        calls=[]
        class Response:
            status=302
            def read(self,n):return b'not persisted'
            def getheaders(self):return [("Location","https://attacker.example"),("X-RateLimit-Requests-Remaining","48")]
        class Connection:
            def __init__(self,host,timeout):calls.append(host)
            def request(self,method,path,headers):calls.append((method,path,headers))
            def getresponse(self):return Response()
            def close(self):pass
        result=RapidApiRedditReader(lambda:"fixture-only",Connection).read(RedditRequest("DesignAndAI"),read_registry())
        self.assertEqual(calls[0],HOST)
        self.assertEqual(len(calls),2)
        self.assertEqual(calls[1][2]["x-rapidapi-key"],"fixture-only")
        self.assertEqual(result.reason,"source_http_302")
        self.assertNotIn("fixture-only",json.dumps(result.report()))
        self.assertEqual(result.quota["requests_remaining"],48)


if __name__=="__main__":unittest.main()
