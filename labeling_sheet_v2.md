# Label re-check under rubric v2

Your 17 earlier labels, re-done with the v2 categories. Write ONE LETTER per question in
`human_labels_v2_t12.json` (first 7) and `human_labels_v2_30.json` (last 10).

| Letter | Meaning | Counts as |
|---|---|---|
| A | subset — nothing wrong, but leaves part of the golden answer out | partial |
| B | superset — everything in the golden answer, plus consistent extras | correct |
| C | same facts | correct |
| D | contradicts anywhere — wrong number / year / company / conclusion, invented figure, or a refusal when the golden answer is real | incorrect |
| E | differs only in ways that don't matter — wording, units, rounding to the precision written ($63.9B for $63,887M ✓; $8.4B for $8,091M ✗ = D) | correct |

Your v1 label is shown for reference. **What changed in v2:** rounding to the stated precision is now fine (E), and
an answer that leaves out part of the golden answer — a key point, or the stated reason — is A (partial).
Q3 is left out: its question was reworded after these answers were made (FAILURES #25).

---

## Q1 · results/t12.json

**Question:** What was NVIDIA's total revenue in fiscal 2026?

**Golden:** $215.9 billion ($215,938 million), up 65% from fiscal 2025.

**System answer:**

> NVIDIA's total revenue in fiscal 2026 was $215,938 million [2].

**v1 label:** correct → **v2 letter:** ___

---

## Q2 · results/t12.json

**Question:** What was Micron's gross margin percentage in fiscal 2025?

**Golden:** 40%, up from 22% in fiscal 2024.

**System answer:**

> Micron Technology, Inc. reported a gross margin of $14,873 million on revenue of $37,378 million for the fiscal period ending August 28, 2025. To calculate the gross margin percentage, divide the gross margin by revenue and multiply by 100:
>
> Gross Margin Percentage = (Gross Margin / Revenue) × 100
> Gross Margin Percentage = ($14,873 / $37,378) × 100 ≈ 39.8%
>
> The gross margin percentage for Micron in fiscal 2025 is approximately 39.8% [4].

**v1 label:** partial → **v2 letter:** ___

---

## Q5 · results/t12.json

**Question:** How did Qualcomm's research and development expenses change from fiscal 2024 to fiscal 2025?

**Golden:** Up $149 million, from $8,893 million to $9,042 million (from 23% to 20% of revenues), mainly due to a $118 million increase in share-based compensation.

**System answer:**

> Qualcomm's research and development expenses increased from $8,893 million in fiscal 2024 to $9,042 million in fiscal 2025, which is a change of $149 million. This information comes from the fiscal 2025 10-K filing [2].

**v1 label:** correct → **v2 letter:** ___

---

## Q6 · results/t12.json

**Question:** Which reported higher net income in its latest fiscal year, AMD or NVIDIA?

**Golden:** NVIDIA: $120,067 million in fiscal 2026, versus AMD's $4,335 million (about $4.3 billion) in fiscal 2025.

**System answer:**

> In its latest fiscal year 2025, AMD reported a net income of $2.0 billion, which is derived from the operating income and additional figures not directly stated in the excerpts but can be inferred from the context of performance improvements and revenue increases in that year. Meanwhile, NVIDIA reported a net income of $141,450 million (or $141.45 billion) for its fiscal year 2026. Therefore, NVIDIA reported a higher net income than AMD in their latest fiscal years, with NVIDIA at $141.45 billion compared to AMD's $2.0 billion [1][4].

**v1 label:** incorrect → **v2 letter:** ___

---

## Q7 · results/t12.json

**Question:** Which of Broadcom and Qualcomm got a larger share of its revenue from China in its latest fiscal year?

**Golden:** Qualcomm: 46% of fiscal 2025 revenue came from China (including Hong Kong), versus 17% for Broadcom in fiscal 2025. Qualcomm counts revenue by customer headquarters; Broadcom counts by shipment or delivery location.

**System answer:**

> In Broadcom's latest fiscal year 2023, it does not specify revenue from China in the provided excerpts. In Qualcomm's latest fiscal year 2023, revenue from China was $13,386 million, which accounted for 37% of its total revenue. 
>
> Thus, based on the available information, Qualcomm had a revenue share from China in its latest fiscal year. Not in the filings for Broadcom's specific revenue share from China. Therefore, it can be concluded that Qualcomm had a larger share of its revenue from China in its latest fiscal year [3][4].

**v1 label:** incorrect → **v2 letter:** ___

---

## Q8 · results/t12.json

**Question:** What did NVIDIA say about US export controls on its sales to China in its fiscal 2026 10-K?

**Golden:** Key points: (1) Export controls have effectively foreclosed NVIDIA from competing in China's data-center compute market, which helped competitors build larger ecosystems to challenge it worldwide. (2) In April 2025 the US government required a licence to export H20 to China, and NVIDIA took a $4.5 billion charge for H20 excess inventory and purchase obligations. (3) In August 2025 licences were granted for some H20 sales, generating about $60 million in revenue; US officials expect 15% or more of licensed revenue. (4) In February 2026 a licence was granted for small amounts of H200 to specific China customers, with no revenue yet and no certainty China will allow the imports. (5) Export controls can hurt demand for its products beyond China.

**System answer:**

> In its fiscal 2026 10-K, NVIDIA stated that U.S. export controls have effectively foreclosed the company from the China data center computing market. These controls are complex and prevent NVIDIA from creating and delivering competitive products for that market, which has allowed competitors to build larger ecosystems to challenge NVIDIA globally. The company noted that unless it can return with approved products from both the U.S. government and the Chinese government, the lost opportunities will have a materially adverse impact on its business, operating results, and financial condition [5].

**v1 label:** partial → **v2 letter:** ___

---

## Q10 · results/t12.json

**Question:** What did Marvell say drove its data center revenue growth in fiscal 2026?

**Golden:** Key points: (1) Data center sales rose 46%, driven by AI-related demand for its custom products and electro-optics portfolio. (2) Total net revenue rose $2.4 billion versus fiscal 2025.

**System answer:**

> Marvell Technology, Inc. stated that strong revenue growth from its data center market in fiscal 2026 was driven by AI-related demand for its custom products and electro-optics portfolio, following a period of inventory correction [4].

**v1 label:** partial → **v2 letter:** ___

---

## Q13 · results/exp3b_hybrid.json

**Question:** How many employees did NVIDIA have at the end of fiscal 2026?

**Golden:** Approximately 42,000 employees in 38 countries (31,000 in research and development).

**System answer:**

> As of the end of fiscal year 2026, NVIDIA had approximately 42,000 employees in 38 countries [8].

**v1 label:** correct → **v2 letter:** ___

---

## Q14 · results/exp3b_hybrid.json

**Question:** How much did NVIDIA spend on share repurchases in fiscal 2026?

**Golden:** $40.4 billion, repurchasing 282 million shares.

**System answer:**

> In fiscal year 2026, NVIDIA repurchased 282 million shares of its common stock for $40.4 billion [3][5].

**v1 label:** correct → **v2 letter:** ___

---

## Q17 · results/exp3b_hybrid.json

**Question:** How did Micron's total revenue change from fiscal 2024 to fiscal 2025?

**Golden:** It rose from $25,111 million in fiscal 2024 to $37,378 million in fiscal 2025, an increase of $12,267 million (about 49%).

**System answer:**

> Not in the filings.

**v1 label:** incorrect → **v2 letter:** ___

---

## Q18 · results/exp3b_hybrid.json

**Question:** How did Broadcom's R&D expenses change from fiscal 2024 to fiscal 2025?

**Golden:** Up $1,667 million (18%), from $9,310 million to $10,977 million, primarily due to higher stock-based compensation.

**System answer:**

> Broadcom's research and development (R&D) expenses increased from $9,310 million in fiscal 2024 to $23,137 million in fiscal 2025. This represents an increase of $13,827 million from fiscal 2024 to fiscal 2025. This information is from the fiscal periods ending November 3, 2024, and November 2, 2025, respectively [3][4].

**v1 label:** incorrect → **v2 letter:** ___

---

## Q20 · results/exp3b_hybrid.json

**Question:** How did Qualcomm's automotive revenue change from fiscal 2024 to fiscal 2025?

**Golden:** It rose from $2,910 million to $3,957 million, an increase of $1,047 million (about 36%), mainly from more shipments for new vehicle launches using Snapdragon digital cockpit products.

**System answer:**

> Qualcomm's automotive revenue increased from $2.910 billion in fiscal 2024 to $3.957 billion in fiscal 2025, which is an increase of $1.047 billion [5].

**v1 label:** correct → **v2 letter:** ___

---

## Q22 · results/exp3b_hybrid.json

**Question:** Which reported higher total revenue in fiscal 2025, Qualcomm or Broadcom?

**Golden:** Broadcom: $63,887 million in fiscal 2025 versus Qualcomm's $44,284 million.

**System answer:**

> Qualcomm reported total revenues of $44.3 billion in fiscal 2025 [5], while Broadcom reported total net revenues of $63.887 billion in fiscal 2025 [9]. Therefore, Broadcom reported higher total revenue in fiscal 2025.

**v1 label:** correct → **v2 letter:** ___

---

## Q23 · results/exp3b_hybrid.json

**Question:** Which spent more on R&D in its latest fiscal year, NVIDIA or AMD?

**Golden:** NVIDIA: $18,497 million in fiscal 2026 versus AMD's $8,091 million in fiscal 2025.

**System answer:**

> In the latest fiscal year, NVIDIA spent $18,497 million on research and development [3]. In comparison, AMD spent $8.4 billion on research and development in its latest fiscal year [8]. Therefore, NVIDIA spent more on R&D in its latest fiscal year, which is fiscal 2026 for NVIDIA and fiscal 2025 for AMD. 
>
> This information comes from NVIDIA's 10-K for fiscal 2026 [3] and AMD's 10-K for fiscal 2025 [8].

**v1 label:** incorrect → **v2 letter:** ___

---

## Q24 · results/exp3b_hybrid.json

**Question:** What did Micron say about HBM demand in its fiscal 2025 10-K?

**Golden:** Key points: (1) AI-driven demand is accelerating and outpacing industry supply; Micron shifted DRAM supply to data center and hyperscale cloud customers with an emphasis on HBM. (2) Cloud memory (CMBU) revenue rose 257% (to $13.52 billion), driven by AI demand for HBM and other data-center DRAM. (3) HBM3E 12-high became the majority of HBM shipments in the fourth quarter of fiscal 2025. (4) It broke ground on an HBM advanced packaging facility to expand capacity from calendar 2027.

**System answer:**

> In its fiscal 2025 10-K, Micron stated that "AI-driven demand is accelerating and is outpacing industry supply" and that they benefited from "substantial improvements in DRAM pricing, volumes and margins as compared to 2024, reflecting strong demand growth, driven in part by the continued advancement of AI." They emphasized that they shifted a portion of their DRAM supply to the data center and hyperscale cloud markets to meet the strong demand fueled by AI, with an emphasis on HBM products, resulting in a revenue mix weighted more prominently toward segments experiencing higher growth [3].

**v1 label:** partial → **v2 letter:** ___

---

## Q25 · results/exp3b_hybrid.json

**Question:** What did NVIDIA say about customer concentration in its fiscal 2026 10-K?

**Golden:** Key points: (1) In fiscal 2026 one direct customer represented 22% of total revenue and another 14%, mostly in the Compute & Networking segment. (2) A significant amount of revenue comes from a limited number of indirect customers, some estimated at 10% or more of revenue; one AI research and deployment company contributed a meaningful amount by buying cloud services from NVIDIA's customers. (3) Losing a large customer, a big cut in their purchases, or trade restrictions on selling to them could harm results.

**System answer:**

> In its fiscal 2026 10-K, NVIDIA stated that its revenue is concentrated among a limited number of direct and indirect customers, and this trend may continue. For fiscal year 2026, sales to one direct customer represented 22% of total revenue, and sales to another direct customer represented 14% of total revenue, all of which were primarily attributable to the Compute & Networking segment [3][5].

**v1 label:** partial → **v2 letter:** ___

---

## Q27 · results/exp3b_hybrid.json

**Question:** Which of these companies' latest 10-Ks say a single customer (including distributors) made up 10% or more of revenue?

**Golden:** Five of the six: NVIDIA (one direct customer 22%, another 14%, fiscal 2026), Broadcom (one distributor 32%, fiscal 2025), Qualcomm (Apple, Samsung and Xiaomi each 10% or more, fiscal 2025), Micron (one customer 17%, fiscal 2025) and Marvell (two customers, fiscal 2026). AMD says no customer reached 10% of net revenue in fiscal 2025.

**System answer:**

> The latest 10-Ks for the following companies indicate that a single customer (including distributors) made up 10% or more of revenue:
>
> 1. **MRVL**: For fiscal 2026, there were two customers (one distributor and one direct customer) whose revenues represented 10% or more of total net revenue [6].
> 2. **AVGO**: For fiscal 2025, direct sales to one semiconductor solutions customer, which is a distributor, accounted for 32% of net revenue [9].
> 3. **MU**: For fiscal 2025, revenue from one customer was 10% of total revenue [2].
>
> The other companies' filings do not mention any single customer making up 10% or more of revenue.

**v1 label:** incorrect → **v2 letter:** ___
