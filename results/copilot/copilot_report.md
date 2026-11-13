# Copilot in Edge: analysis of recordings

## E1_run1.flow

- 60 requests to 9 hosts; third-party hosts: none
- prompts sent: 3; server requests for browser content: 3; page uploads: 3
- metadata sent with prompts: locationInfo={"timeZoneOffset": -5, "timeZone": "America/Toronto"}, locale=en-us
- server asked `fetch_browser_content` (contentType=web_page, tabidList=["1924331258"], userLocation=CA-QC)
- server asked `fetch_browser_content` (contentType=web_page, tabidList=["1924331263"], userLocation=CA-QC)
- server asked `fetch_browser_content` (contentType=web_page, tabidList=["1924331268"], userLocation=CA-QC)

**Markers found in traffic sent from the browser:**

- `e1_article` (ZQX-E1-ART-2207) -> substrate.office.com (Microsoft)
- `e1_form_ref` (ZQX-E1-FRM-6612) -> substrate.office.com (Microsoft)
- `e1_form_name` (Avery Quinlan) -> substrate.office.com (Microsoft)
- `e1_form_email` (avery.q.soen321@example.org) -> substrate.office.com (Microsoft)
- `e1_form_memberid` (NCC-48213) -> substrate.office.com (Microsoft)
- `e1_health_ref` (ZQX-E1-HLT-3381) -> substrate.office.com (Microsoft)
- `e1_health_card` (QNLA-7104-1882) -> substrate.office.com (Microsoft)
- `e1_health_diagnosis` (type 2 diabetes) -> substrate.office.com (Microsoft)

**Page content uploaded to Copilot:**

- http://127.0.0.1:8765/e1_article.html (Urban gardening on small balconies): 704 chars

  > Urban gardening on small balconies Article reference ZQX-E1-ART-2207 Balcony gardens have become popular in dense cities. Even a two-square-metre balcony can grow herbs, cherry tomatoes and lettuce if it gets at least five hours of sun. Containers should have drainage holes, and lightweight potting mix keeps the load on the balcony low. Watering is the most common problem. Small pots dry out quickly in summer, so many growers use self-watering containers or drip lines on a timer. Mulch on top of the soil also slows evaporation. Wind is the second problem on high floors. A simple mesh screen protects plants without blocking light. Choosing compact varieties, such as dwarf tomatoes, helps as well.

- http://127.0.0.1:8765/e1_form.html (Member registration - Northfield Community Centre): 297 chars

  > Member registration Northfield Community Centre. Fill in the form to register for the fall programme. Form reference ZQX-E1-FRM-6612. Full name Avery Quinlan Email avery.q.soen321@example.org Phone [Phone Number Redacted] Member ID NCC-48213 Home address [Address Redacted] Register (do not click)

- http://127.0.0.1:8765/e1_health.html (Patient portal - Lab results): 447 chars

  > Patient portal: lab results Patient: Avery Quinlan   Date of birth: 1971-04-18   Health card: QNLA-7104-1882 Result reference: ZQX-E1-HLT-3381 Test Result Range HbA1c 7.9 % 4.0 - 5.6 % Fasting glucose 9.1 mmol/L 3.9 - 5.5 mmol/L TSH 2.1 mIU/L 0.4 - 4.0 mIU/L Physician note: Results consistent with type 2 diabetes. Start metformin 500 mg twice daily. Follow-up in 3 months. All data on this page is fictional, created for a university experiment.


## E1_run2.flow

- 44 requests to 9 hosts; third-party hosts: none
- prompts sent: 3; server requests for browser content: 3; page uploads: 3
- metadata sent with prompts: locationInfo={"timeZoneOffset": -5, "timeZone": "America/Toronto"}, locale=en-us
- server asked `fetch_browser_content` (contentType=web_page, tabidList=["1924331324"], userLocation=CA-QC)
- server asked `fetch_browser_content` (contentType=web_page, tabidList=["1924331329"], userLocation=CA-QC)
- server asked `fetch_browser_content` (contentType=web_page, tabidList=["1924331334"], userLocation=CA-QC)

**Markers found in traffic sent from the browser:**

- `e1_article` (ZQX-E1-ART-2207) -> substrate.office.com (Microsoft)
- `e1_form_ref` (ZQX-E1-FRM-6612) -> substrate.office.com (Microsoft)
- `e1_form_name` (Avery Quinlan) -> substrate.office.com (Microsoft)
- `e1_form_email` (avery.q.soen321@example.org) -> substrate.office.com (Microsoft)
- `e1_form_memberid` (NCC-48213) -> substrate.office.com (Microsoft)
- `e1_health_ref` (ZQX-E1-HLT-3381) -> substrate.office.com (Microsoft)
- `e1_health_card` (QNLA-7104-1882) -> substrate.office.com (Microsoft)
- `e1_health_diagnosis` (type 2 diabetes) -> substrate.office.com (Microsoft)

**Page content uploaded to Copilot:**

- http://127.0.0.1:8765/e1_article.html (Urban gardening on small balconies): 704 chars

  > Urban gardening on small balconies Article reference ZQX-E1-ART-2207 Balcony gardens have become popular in dense cities. Even a two-square-metre balcony can grow herbs, cherry tomatoes and lettuce if it gets at least five hours of sun. Containers should have drainage holes, and lightweight potting mix keeps the load on the balcony low. Watering is the most common problem. Small pots dry out quickly in summer, so many growers use self-watering containers or drip lines on a timer. Mulch on top of the soil also slows evaporation. Wind is the second problem on high floors. A simple mesh screen protects plants without blocking light. Choosing compact varieties, such as dwarf tomatoes, helps as well.

- http://127.0.0.1:8765/e1_form.html (Member registration - Northfield Community Centre): 297 chars

  > Member registration Northfield Community Centre. Fill in the form to register for the fall programme. Form reference ZQX-E1-FRM-6612. Full name Avery Quinlan Email avery.q.soen321@example.org Phone [Phone Number Redacted] Member ID NCC-48213 Home address [Address Redacted] Register (do not click)

- http://127.0.0.1:8765/e1_health.html (Patient portal - Lab results): 447 chars

  > Patient portal: lab results Patient: Avery Quinlan   Date of birth: 1971-04-18   Health card: QNLA-7104-1882 Result reference: ZQX-E1-HLT-3381 Test Result Range HbA1c 7.9 % 4.0 - 5.6 % Fasting glucose 9.1 mmol/L 3.9 - 5.5 mmol/L TSH 2.1 mIU/L 0.4 - 4.0 mIU/L Physician note: Results consistent with type 2 diabetes. Start metformin 500 mg twice daily. Follow-up in 3 months. All data on this page is fictional, created for a university experiment.


## E2_run1.flow

- 165 requests to 13 hosts; third-party hosts: none
- prompts sent: 8; server requests for browser content: 0; page uploads: 0
- metadata sent with prompts: locationInfo={"timeZoneOffset": -5, "timeZone": "America/Toronto"}, locale=en-us

**Markers found in traffic sent from the browser:**


**Page content uploaded to Copilot:**


## E2_run2.flow

- 227 requests to 13 hosts; third-party hosts: none
- prompts sent: 13; server requests for browser content: 0; page uploads: 0
- metadata sent with prompts: locationInfo={"timeZoneOffset": -5, "timeZone": "America/Toronto"}, locale=en-us

**Markers found in traffic sent from the browser:**


**Page content uploaded to Copilot:**


## E2_run3.flow

- 239 requests to 13 hosts; third-party hosts: none
- prompts sent: 15; server requests for browser content: 0; page uploads: 0
- metadata sent with prompts: locationInfo={"timeZoneOffset": -5, "timeZone": "America/Toronto"}, locale=en-us

**Markers found in traffic sent from the browser:**


**Page content uploaded to Copilot:**


## E2_run4.flow

- 191 requests to 17 hosts; third-party hosts: none
- prompts sent: 11; server requests for browser content: 0; page uploads: 0
- metadata sent with prompts: locationInfo={"timeZoneOffset": -5, "timeZone": "America/Toronto"}, locale=en-us

**Markers found in traffic sent from the browser:**


**Page content uploaded to Copilot:**


## E3_run1.flow

- 30 requests to 10 hosts; third-party hosts: none
- prompts sent: 1; server requests for browser content: 1; page uploads: 1
- metadata sent with prompts: locationInfo={"timeZoneOffset": -5, "timeZone": "America/Toronto"}, locale=en-us
- server asked `fetch_browser_content` (contentType=web_page, tabidList=["1924331288"], userLocation=CA-QC)

**Markers found in traffic sent from the browser:**

- `e3_top` (ZQX-E3-TOP-1043) -> substrate.office.com (Microsoft)
- `e3_mid` (ZQX-E3-MID-5527) -> substrate.office.com (Microsoft)
- `e3_bottom` (ZQX-E3-BOT-9904) -> substrate.office.com (Microsoft)

**Page content uploaded to Copilot:**

- http://127.0.0.1:8765/e3_long.html (City services annual review): 19618 chars

  > City services annual review Section 1 reference: ZQX-E3-TOP-1043 Municipal planning in mid-sized cities often balances housing density against green space. Public transit ridership tends to recover slowly after service cuts, because riders change habits. Bike lanes separated by curbs see far more use than painted lanes, according to several city reports. Libraries have expanded into community hubs, lending tools, offering study rooms and hosting clinics. Winter maintenance budgets are dominated by snow removal on secondary streets and sidewalks. Public transit ridership tends to recover slowly after service cuts, because riders change habits. Bike lanes separated by curbs see far more use than painted lanes, according to several city reports. Libraries have expanded into community hubs, lending tools, offering study rooms and hosting clinics. Winter maintenance budgets are dominated by snow removal on secondary streets and sidewalks. Municipal planning in mid-sized cities often balances housing density against green space. Bike lanes separated by curbs see far more use than painted lanes, according to several city reports. Libraries have expanded into community hubs, lending tools, offering study rooms and hosting clinics. Winter maintenance budgets are dominated by snow removal on secondary streets and sidewalks. Municipal planning in mid-sized cities often balances housing density against green space. Public transit ridership tends to recover slowly after service cuts, beca


## E3_run2.flow

- 26 requests to 9 hosts; third-party hosts: none
- prompts sent: 1; server requests for browser content: 1; page uploads: 1
- metadata sent with prompts: locationInfo={"timeZoneOffset": -5, "timeZone": "America/Toronto"}, locale=en-us
- server asked `fetch_browser_content` (contentType=web_page, tabidList=["1924331360"], userLocation=CA-QC)

**Markers found in traffic sent from the browser:**

- `e3_top` (ZQX-E3-TOP-1043) -> substrate.office.com (Microsoft)
- `e3_mid` (ZQX-E3-MID-5527) -> substrate.office.com (Microsoft)
- `e3_bottom` (ZQX-E3-BOT-9904) -> substrate.office.com (Microsoft)

**Page content uploaded to Copilot:**

- http://127.0.0.1:8765/e3_long.html (City services annual review): 19618 chars

  > City services annual review Section 1 reference: ZQX-E3-TOP-1043 Municipal planning in mid-sized cities often balances housing density against green space. Public transit ridership tends to recover slowly after service cuts, because riders change habits. Bike lanes separated by curbs see far more use than painted lanes, according to several city reports. Libraries have expanded into community hubs, lending tools, offering study rooms and hosting clinics. Winter maintenance budgets are dominated by snow removal on secondary streets and sidewalks. Public transit ridership tends to recover slowly after service cuts, because riders change habits. Bike lanes separated by curbs see far more use than painted lanes, according to several city reports. Libraries have expanded into community hubs, lending tools, offering study rooms and hosting clinics. Winter maintenance budgets are dominated by snow removal on secondary streets and sidewalks. Municipal planning in mid-sized cities often balances housing density against green space. Bike lanes separated by curbs see far more use than painted lanes, according to several city reports. Libraries have expanded into community hubs, lending tools, offering study rooms and hosting clinics. Winter maintenance budgets are dominated by snow removal on secondary streets and sidewalks. Municipal planning in mid-sized cities often balances housing density against green space. Public transit ridership tends to recover slowly after service cuts, beca


## E4_run1.flow

- 34 requests to 9 hosts; third-party hosts: none
- prompts sent: 2; server requests for browser content: 2; page uploads: 2
- metadata sent with prompts: locationInfo={"timeZoneOffset": -5, "timeZone": "America/Toronto"}, locale=en-us
- server asked `fetch_browser_content` (contentType=web_page, tabidList=["1924331306"], userLocation=CA-QC)
- server asked `fetch_browser_content` (contentType=web_page, tabidList=["1924331306","1924331311","1924331244"], userLocation=CA-QC)

**Markers found in traffic sent from the browser:**

- `e4_tabA` (ZQX-TABA-1188) -> substrate.office.com (Microsoft)
- `e4_tabA_name` (Jordan Ellery) -> substrate.office.com (Microsoft)
- `e4_tabB` (ZQX-TABB-5520) -> substrate.office.com (Microsoft)
- `e4_tabB_name` (Morgan Pike) -> substrate.office.com (Microsoft)

**Page content uploaded to Copilot:**

- http://127.0.0.1:8765/e4_tabA.html (Order confirmation): 182 chars

  > Order confirmation Thank you, Jordan Ellery . Your order ZQX-TABA-1188 has shipped. Items: 1 x trail running shoes (size 10), 1 x rain jacket. Delivery to 22 Fake Crescent, Gatineau.

- http://127.0.0.1:8765/e4_tabA.html (Order confirmation): 182 chars

  > Order confirmation Thank you, Jordan Ellery . Your order ZQX-TABA-1188 has shipped. Items: 1 x trail running shoes (size 10), 1 x rain jacket. Delivery to 22 Fake Crescent, Gatineau.


## E4_run2.flow

- 31 requests to 9 hosts; third-party hosts: none
- prompts sent: 2; server requests for browser content: 1; page uploads: 1
- metadata sent with prompts: locationInfo={"timeZoneOffset": -5, "timeZone": "America/Toronto"}, locale=en-us
- server asked `fetch_browser_content` (contentType=web_page, tabidList=["1924331378"], userLocation=CA-QC)

**Markers found in traffic sent from the browser:**

- `e4_tabA` (ZQX-TABA-1188) -> substrate.office.com (Microsoft)
- `e4_tabA_name` (Jordan Ellery) -> substrate.office.com (Microsoft)

**Page content uploaded to Copilot:**

- http://127.0.0.1:8765/e4_tabA.html (Order confirmation): 182 chars

  > Order confirmation Thank you, Jordan Ellery . Your order ZQX-TABA-1188 has shipped. Items: 1 x trail running shoes (size 10), 1 x rain jacket. Delivery to 22 Fake Crescent, Gatineau.

