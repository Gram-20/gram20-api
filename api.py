#!/usr/bin/env python
import math
import base64

from fastapi import FastAPI, HTTPException, Depends, Security, Request, Cookie, Header
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import codecs
import decimal
from time import time
from loguru import logger

app = FastAPI(
    title="GRAM-20 API",
    version="0.2.0"
)

api_pool = psycopg2.pool.SimpleConnectionPool(1, 50)
class SafeConn:
    def __init__(self, pool):
        self.pool = pool

    def __enter__(self):
        self.conn = self.pool.getconn()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pool.putconn(self.conn)

api_conn = SafeConn(api_pool)


def calc_crc(message):
    poly = 0x1021
    reg = 0
    message += b'\x00\x00'
    for byte in message:
        mask = 0x80
        while (mask > 0):
            reg <<= 1
            if byte & mask:
                reg += 1
            mask >>= 1
            if reg > 0xffff:
                reg &= 0xffff
                reg ^= poly
    return reg.to_bytes(2, "big")

def normalize_address(addr: str):
    try:
        r = base64.urlsafe_b64decode(addr)
        addr = b'\x11' + r[1:34]
        return codecs.decode(codecs.encode(addr + calc_crc(addr), "base64"), "utf-8").strip() \
            .replace('/', '_').replace("+", '-')
    except:
        return addr

@app.get("/v1/gram20/balance/{address}/{tick}")
async def balance(address: str, tick: str):
    address = normalize_address(address)
    with api_conn as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as api_cursor:
            api_cursor.execute("""select  * from gram20_ledger gl where "owner"  = %s and tick = %s
            order by id desc limit 1""", (address, tick))
            res = api_cursor.fetchone()
            balance = 0
            if res:
                balance = res['balance']
            return {
                "address": address,
                'tick': tick,
                'balance': balance
            }

@app.get("/v1/gram20/check")
async def check_hash(hash: str):
    with api_conn as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as api_cursor:
            api_cursor.execute("""select 1 from gram20_ledger gl where "hash"  = %s """, (hash, ))
            res = api_cursor.fetchone()
            if res:
                return {
                    "status": "OK"
                }
            else:
                api_cursor.execute("""select * from gram20_rejection gr 
                join messages m using(msg_id)
                where hash =  %s """, (hash, ))
                res = api_cursor.fetchone()
                if res:
                    return {
                        "status": "Rejected"
                    }
                else:
                    return {
                        "status": "Not found"
                    }

@app.get("/v1/gram20/history/{address}/{tick}")
async def history(address: str, tick: str, max_id: int = 0):
    address = normalize_address(address)
    with api_conn as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as api_cursor:
            if max_id > 0:
                api_cursor.execute("""
                select id, utime, hash, delta, comment, peer, lt from gram20_ledger where "action"  > 0 and 
                "owner" = %s and tick = %s and id < %s
                order by id desc
                limit 10
                """, (address, tick, max_id))
            else:
                api_cursor.execute("""
                select id, utime, hash, delta, comment, peer, lt from gram20_ledger where "action"  > 0 and 
                "owner" = %s and tick = %s
                order by id desc
                limit 10
                """, (address, tick))
            res = []
            for row in api_cursor.fetchall():
                res.append({
                    'address': address,
                    'tick': tick,
                    'time': row['utime'],
                    'hash': row['hash'],
                    'delta': row['delta'],
                    'comment': row['comment'],
                    'peer': row['peer'],
                    'lt': row['lt'],
                    'id': row['id'],
                })
            return res


@app.get("/v1/gram20/balance/{address}")
async def balance_all(address: str):
    address = normalize_address(address)
    with api_conn as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as api_cursor:
            api_cursor.execute("""select  distinct on (owner, tick) tick, balance from gram20_ledger gl where "owner"  = %s 
            order by owner, tick, id desc""", (address,))
            res = []
            for row in api_cursor.fetchall():
                res.append({
                        "address": address,
                        'tick': row['tick'],
                        'balance': row['balance']
                    })
            return res

@app.get("/v1/gram20/tick/{tick}")
async def get_tick_info(tick: str):
    if tick:
        tick = tick.lower()

    with api_conn as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as api_cursor:
            api_cursor.execute("""
    select address, utime, hash, owner, tick, mint_limit, max_supply, supply from gram20_token gt
    where tick = %s
            """, (tick,))
            row = api_cursor.fetchone()
            if not row:
                return {}
            res = {
                    'tick': row['tick'],
                    'total_supply': row['max_supply'],
                    'supply': row['supply'],
                    'mintable': row['supply'] < row['max_supply'],
                    'mint_limit': row['mint_limit'],
                    'address': row['address'],
                    'deploy_time': row['utime'],
                    'deploy_hash': row['hash'],
                    'owner': row['owner']
                }

            return res