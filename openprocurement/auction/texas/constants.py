# -*- coding: utf-8 -*-
from datetime import timedelta

ROUND_DURATION = 180
PAUSE_DURATION = 10
BIDS_KEYS_FOR_COPY = ("bidder_id", "time")
AUCTION_SUBPATH = 'texas-auctions'
MULTILINGUAL_FIELDS = ["title", "description"]
ADDITIONAL_LANGUAGES = ["ru", "en"]

PRESTARTED = 'pre-started'
MAIN_ROUND = 'english'
PAUSE = 'pause'
AUCTION_DEADLINE = 'auction-deadline'
PREANNOUNCEMENT = 'pre-announcement'
END = 'announcement'

DEADLINE_HOUR = 17
SANDBOX_AUCTION_DURATION = timedelta(minutes=30)

DEFAULT_AUCTION_TYPE = 'texas'
