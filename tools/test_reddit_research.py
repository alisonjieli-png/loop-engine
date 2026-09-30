import json
from pathlib import Path
import tempfile
import unittest

from knowledge_radar.rapidapi_reddit import RedditObservation, parse_posts
from read_reddit_research import STATE_ID, read_once
from knowledge_radar.community_store import CommunityStore
from test_rapidapi_reddit import body, post


class IntakeChecks(unittest.TestCase):
    def test_no_grant_means_no_state_or_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/"private"
            answer=read_once(path)
            self.assertFalse(answer["effects_performed"])
            self.assertFalse(path.exists())

    def test_request_queues_existing_work_and_repeat_respects_provider_window(self):
        class Reader:
            calls=0
            def read(self,request,registry):
                self.calls+=1
                leads,coverage=parse_posts(body(post()),request,registry)
                return RedditObservation(200,.1,100,"a"*64,leads,coverage,
                    {"requests_remaining":2,"reset_at_unix":1791050400})
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/"private";reader=Reader()
            first=read_once(path,subreddit="DesignAndAI",authorized=True,reader=reader,now=1790791200)
            self.assertEqual(first["status"],"complete")
            self.assertEqual(first["intake"]["added"],1)
            self.assertEqual(first["work_orders_compiled"],1)
            second=read_once(path,authorized=True,reader=reader,now=1790791201)
            self.assertEqual(second["status"],"not_due")
            self.assertEqual(reader.calls,1)
            self.assertEqual(CommunityStore(path).get(STATE_ID)["document"]["data"]["next_read_at_unix"],1790920800)

    def test_unknown_outcome_stops_automatic_replay(self):
        class Reader:
            calls=0
            def read(self,*args):
                self.calls+=1
                return RedditObservation(0,25,0,"",reason="source_outcome_unknown")
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/"private";reader=Reader()
            first=read_once(path,authorized=True,reader=reader,now=1790791200)
            self.assertEqual(first["status"],"failed")
            second=read_once(path,authorized=True,reader=reader,now=1791091200)
            self.assertEqual(second["status"],"unknown_request_requires_reconciliation")
            self.assertEqual(reader.calls,1)


if __name__=="__main__":unittest.main()
