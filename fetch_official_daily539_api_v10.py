#!/usr/bin/env python3
"""539 official-site API evidence capture v10; append-only evidence package only.
The endpoint is a website-internal API, not a published/stable API contract.
No master dataset or Registry file is modified.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
import requests

API = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Daily539Result"
PAGE_SIZE = 50
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; 539-period-evidence-audit/10.0)",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.taiwanlottery.com/",
}

def norm_nums(value):
    vals = value[:5] if isinstance(value, list) else re.findall(r"\d+", str(value))[:5]
    try:
        nums = sorted(int(v) for v in vals)
        if len(nums) != 5 or len(set(nums)) != 5 or any(n < 1 or n > 39 for n in nums): return ""
        return " ".join(f"{n:02d}" for n in nums)
    except Exception: return ""

def parse_api(data):
    if not isinstance(data, dict) or not isinstance(data.get("content"), dict): raise ValueError("INVALID_TOP_LEVEL_SCHEMA")
    arr = data["content"].get("daily539Res")
    if not isinstance(arr, list): raise ValueError("MISSING_OR_INVALID_content.daily539Res")
    out=[]
    for i, r in enumerate(arr):
        if not isinstance(r, dict): raise ValueError(f"ROW_{i}_NOT_OBJECT")
        raw_date=str(r.get("lotteryDate", ""))
        try: date=datetime.fromisoformat(raw_date.replace("Z", "+00:00")).date().isoformat()
        except Exception: date=raw_date[:10]
        period=str(r.get("period", "")); nums=norm_nums(r.get("drawNumberAppear", []))
        if not date or not period or not nums: raise ValueError(f"ROW_{i}_MISSING_DATE_PERIOD_OR_VALID_FIVE_NUMBERS")
        out.append({"date":date,"period":period,"numbers":nums})
    return out

def months_between(start, end):
    y,m=map(int,start.split('-')); ey,em=map(int,end.split('-'))
    while (y,m)<=(ey,em):
        yield f"{y:04d}-{m:02d}"
        m+=1
        if m==13: y,m=y+1,1

def selftest():
    fixture={"content":{"daily539Res":[{"period":"115000277","lotteryDate":"2026-11-16T00:00:00","drawNumberAppear":[11,21,22,35,37]}]}}
    assert parse_api(fixture)==[{"date":"2026-11-16","period":"115000277","numbers":"11 21 22 35 37"}]
    for bad in ({},{"content":{}},{"content":{"daily539Res":None}}):
        try: parse_api(bad)
        except ValueError: pass
        else: raise AssertionError("invalid schema accepted")
    return "PASS"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--mode',choices=['probe','full'],default='probe')
    ap.add_argument('--probe-month',default='2026-11')
    ap.add_argument('--input',default='539_906筆次級資料交叉比對_v1.csv')
    ap.add_argument('--out',default='539_v10_capture')
    ap.add_argument('--timeout',type=int,default=20)
    ap.add_argument('--retries',type=int,default=2)
    ap.add_argument('--sleep',type=float,default=0.8)
    args=ap.parse_args()
    out=Path(args.out); rawdir=out/'raw_api_responses'; metadir=out/'metadata'
    rawdir.mkdir(parents=True,exist_ok=True); metadir.mkdir(parents=True,exist_ok=True)
    months=list(months_between('2024-01','2026-11')) if args.mode=='full' else [args.probe_month]
    summary={"version":"v10","endpoint":API,"endpoint_classification":"website-internal API; not a published/stable API contract","selftest":selftest(),"mode":args.mode,"requested_months":months,"captured_months":0,"failed_months":[],"parsed_rows":0,"candidate_rows":0,"exact_date_and_five_number_matches":0,"status":"RUNNING"}
    all_draws=[]; errors=[]; session=requests.Session(); session.headers.update(HEADERS)
    for ix,month in enumerate(months):
        params={"period":"","month":month,"pageNum":1,"pageSize":PAGE_SIZE}
        req=requests.Request('GET',API,params=params).prepare().url
        resp=None; err=None
        for attempt in range(args.retries+1):
            try:
                resp=session.get(API,params=params,timeout=args.timeout); resp.raise_for_status(); break
            except Exception as e:
                err=repr(e)
                if attempt<args.retries: time.sleep(1.5*(attempt+1))
        if resp is None:
            failure={"month":month,"requested_url":req,"error":err}
            errors.append(failure); (metadir/f'{month.replace("-","")}.failure.json').write_text(json.dumps(failure,ensure_ascii=False,indent=2),encoding='utf-8')
            summary['failed_months'].append(month); continue
        body=resp.content; stem=month.replace('-',''); bodyname=f'{stem}.response.bin'; (rawdir/bodyname).write_bytes(body)
        meta={"month":month,"url":resp.url,"captured_at_utc":datetime.now(timezone.utc).isoformat(),"http_status":resp.status_code,"headers":dict(resp.headers),"content_length":len(body),"sha256":hashlib.sha256(body).hexdigest(),"body_file":bodyname}
        try:
            parsed=parse_api(resp.json()); meta['schema_status']='VALID_DAILY539_SCHEMA'; meta['rows_parsed']=len(parsed)
            for row in parsed: row['source_month']=month
            all_draws.extend(parsed); summary['parsed_rows']+=len(parsed)
        except Exception as e:
            parsed=[]; meta['schema_status']='INVALID_OR_UNEXPECTED_SCHEMA'; meta['parse_error']=repr(e)
        (metadir/f'{stem}.metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
        summary['captured_months']+=1
        if ix<len(months)-1: time.sleep(args.sleep)
    # Deduplicate API rows by date+period+numbers; preserve collisions for review.
    bykey={}
    for d in all_draws: bykey.setdefault((d['date'],d['period'],d['numbers']),d)
    draws=sorted(bykey.values(),key=lambda x:(x['date'],x['period']))
    with (out/'official_api_draw_rows.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['date','period','numbers','source_month']); w.writeheader(); w.writerows(draws)
    summary['unique_api_rows']=len(draws)
    if Path(args.input).exists():
        with open(args.input,encoding='utf-8-sig',newline='') as f: candidates=list(csv.DictReader(f))
        idx={(d['date'],d['numbers']):d for d in draws}
        reconciled=[]
        for c in candidates:
            if c.get('official_issue_id'): continue
            date=str(c.get('draw_date',''))[:10]; nums=norm_nums(c.get('expected_numbers',''))
            hit=idx.get((date,nums)); row=dict(c)
            row.update({'api_period_candidate':hit['period'] if hit else '', 'api_evidence_status':'MATCHED_OFFICIAL_API_RAW_RESPONSE_CANDIDATE' if hit else 'NO_EXACT_MATCH_IN_CAPTURED_MONTHS'})
            reconciled.append(row)
        fields=list(dict.fromkeys(k for r in reconciled for k in r))
        with (out/'candidate_period_api_reconciliation.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(reconciled)
        summary['candidate_rows']=len(reconciled); summary['exact_date_and_five_number_matches']=sum(r['api_evidence_status'].startswith('MATCHED_') for r in reconciled)
        summary['warning']='Matches are API-response candidates only. Do not automatically promote period IDs to official master data; human review and append-only evidence overlay required.'
    summary['status']='CAPTURE_COMPLETE' if summary['captured_months']==len(months) else ('PARTIAL_CAPTURE' if summary['captured_months'] else 'BLOCKED_NETWORK_OR_DNS')
    summary['network_failures']=errors
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0 if summary['captured_months'] else 2
if __name__=='__main__': sys.exit(main())
