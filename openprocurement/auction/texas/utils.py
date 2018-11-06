# -*- coding: utf-8 -*-
import iso8601

from contextlib import contextmanager
from datetime import datetime, time, timedelta
from decimal import Decimal

from openprocurement.auction.worker_core.constants import TIMEZONE
from openprocurement.auction.worker_core.utils import prepare_service_stage

from openprocurement.auction.texas.constants import (
    PAUSE_DURATION, END, MAIN_ROUND, PAUSE, ROUND_DURATION
)


def prepare_results_stage(bidder_id="", bidder_name="", amount="", time=""):
    stage = dict(
        bidder_id=bidder_id,
        time=str(time),
        amount=amount or 0,
        label=dict(
            en="Bidder #{}".format(bidder_name),
            uk="Учасник №{}".format(bidder_name),
            ru="Участник №{}".format(bidder_name)
        )
    )
    return stage


def prepare_auction_stages(stage_start, auction_data, deadline_hour, fast_forward=False):
    pause_stage = prepare_service_stage(
        start=stage_start.isoformat(), type=PAUSE
    )
    main_round_stage = {}
    stages = [pause_stage, main_round_stage]

    stage_start += timedelta(seconds=PAUSE_DURATION)

    deadline = set_specific_hour(stage_start, deadline_hour) if deadline_hour else None
    if deadline is None or stage_start < deadline:

        planned_end = stage_start + timedelta(seconds=ROUND_DURATION)
        planned_end = planned_end if deadline is None or planned_end < deadline else deadline
        stage_amount = float(Decimal(auction_data['value']['amount'] +
                                     auction_data['minimalStep']['amount']).quantize(Decimal('0.01')))
        main_round_stage.update({
            'start': stage_start.isoformat(),
            'type': MAIN_ROUND,
            'amount': stage_amount,
            'time': '',
            # This field `planned_end' is needed to display time when round will automatically end if no one post bid
            'planned_end': planned_end.isoformat()
        })

    pause_stage.update({
        'planned_end': stage_start.isoformat() if main_round_stage else deadline.isoformat()
    })

    return stages


def prepare_end_stage(start):
    stage = {
        'start': start.isoformat(),
        'type': END,
    }
    return stage


def get_round_ending_time(start_date, duration, deadline):
    default_round_ending_time = start_date + timedelta(seconds=duration)
    if deadline is None or default_round_ending_time < deadline:
        return default_round_ending_time
    return deadline


def set_specific_hour(date_time, hour):
    """Reset datetime's time to {hour}:00:00, while saving timezone data

    Example:
        2018-1-1T14:12:55+02:00 -> 2018-1-1T02:00:00+02:00, for hour=2
        2018-1-1T14:12:55+02:00 -> 2018-1-1T18:00:00+02:00, for hour=18
    """

    return datetime.combine(
        date_time.date(), time(hour % 24, tzinfo=date_time.tzinfo)
    )


def get_bids(results):

    bids_information = dict([
        (bid["id"], bid)
        for bid in results["data"].get("bids", [])
    ])

    return bids_information


def open_bidders_name(auction_document, bids_information):
    for field in ['initial_bids', 'results', 'stages']:
        for index, stage in enumerate(auction_document[field]):
            if 'bidder_id' in stage and stage['bidder_id'] in bids_information:
                auction_document[field][index].update({
                    'bidNumber': bids_information[stage['bidder_id']].get('bidNumber', ''),
                    "label": {
                        'uk': bids_information[stage['bidder_id']]["tenderers"][0]["name"],
                        'en': bids_information[stage['bidder_id']]["tenderers"][0]["name"],
                        'ru': bids_information[stage['bidder_id']]["tenderers"][0]["name"],
                    }
                })
    return auction_document


@contextmanager
def update_auction_document(context, database):
    auction_document = context['auction_document']
    yield auction_document
    database.save_auction_document(auction_document, context['auction_doc_id'])
    context['auction_document'] = auction_document


@contextmanager
def lock_server(semaphore):
    semaphore.acquire()
    yield
    semaphore.release()


def convert_datetime(datetime_stamp):
    return iso8601.parse_date(datetime_stamp).astimezone(TIMEZONE)


# AUCTION PROTOCOL FUNCTIONS

def prepare_auction_protocol(context):
    auction_protocol = {
        "id": context["auction_doc_id"],
        "auctionId": context["auction_data"]["data"].get("auctionID", ""),
        "auction_id": context["auction_doc_id"],
        "items": context["auction_data"]["data"].get("items", []),
        "timeline": {
            "auction_start": {
                "initial_bids": []
            },

        }
    }
    return auction_protocol


def prepare_bid_result(bid):
    return {
        'bidder': bid['bidder_id'],
        'amount': bid['amount'],
        'time': bid['time']
    }


def approve_auction_protocol_info(auction_document, auction_protocol):
    stages = auction_document['stages']
    for index, stage in enumerate(stages):
        if stage['type'] == MAIN_ROUND and stage.get('time'):
            round_number = index / 2 + 1
            auction_protocol['timeline']['round_{}'.format(round_number)] = prepare_bid_result(stage)
    return auction_protocol


def approve_auction_protocol_info_on_bids_stage(auction_document, auction_protocol):
    current_stage = int(auction_document['current_stage'])
    bid = auction_document['stages'][current_stage]
    round_number = current_stage / 2 + 1
    auction_protocol['timeline']['round_{}'.format(round_number)] = prepare_bid_result(bid)
    return auction_protocol


def approve_auction_protocol_info_on_announcement(auction_document, auction_protocol, approved=None):
    auction_protocol['timeline']['results'] = {
        "time": datetime.now(TIMEZONE).isoformat(),
        "bids": []
    }

    if approved:
        auction_protocol['timeline']['auction_start']['initial_bids'] = []
        for bid in auction_document['initial_bids']:
            auction_protocol['timeline']['auction_start']['initial_bids'].append({
                'bidder': bid['bidder_id'],
                'date': bid['time'],
                'amount': bid['amount'],
                'bid_number': approved[bid['bidder_id']].get('bidNumber', ''),
                'identification': approved[bid['bidder_id']].get('tenderers', []),
                'owner': approved[bid['bidder_id']].get('owner', '')
            })

    for bid in auction_document['results']:
        bid_result_audit = prepare_bid_result(bid)
        if approved:
            bid_result_audit['bid_number'] = approved[bid['bidder_id']].get('bidNumber', '')
            bid_result_audit['identification'] = approved[bid['bidder_id']].get('tenderers', [])
            bid_result_audit['owner'] = approved[bid['bidder_id']].get('owner', '')
        auction_protocol['timeline']['results']['bids'].append(bid_result_audit)
    return auction_protocol
