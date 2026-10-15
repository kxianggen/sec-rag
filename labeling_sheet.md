# Judge re-check — label 10 answers by hand

Answers from `results/exp3b_hybrid.json` (hybrid retrieval = the adopted system).
For each one, write **correct / partial / incorrect** in `human_labels_30.json`.
Grade the SYSTEM answer against the GOLDEN answer. Don't look at the judge's verdicts first.

## The rubric (same rules the judge uses)

- **correct** — every number matches the golden answer (same company, same fiscal year), quoted as the filing states it. Different formatting of the SAME figure is fine ($63,887 million = $63.887 billion). "Which is higher" questions: conclusion right AND numbers right. Narrative: covers the key points, contradicts none.
- **partial** — right company, year and conclusion, but a number is only approximately right (computed or rounded instead of quoted). Narrative: accurate on at least ONE key point and contradicts none, even if it leaves others out.
- **incorrect** — any invented or wrong number, wrong year, wrong company, wrong conclusion, or a refusal when the golden answer is a real answer. Narrative: covers none of the key points, or says something false.

Tip: decide in this order — (1) refused? (2) any wrong number? (3) anything missing or rounded?

---

## Q13 · fact

**Question:** How many employees did NVIDIA have at the end of fiscal 2026?

**Golden answer:** Approximately 42,000 employees in 38 countries (31,000 in research and development).

**System answer:**

> As of the end of fiscal year 2026, NVIDIA had approximately 42,000 employees in 38 countries [8].

**Your label (Q13):** ______

---

## Q14 · fact

**Question:** How much did NVIDIA spend on share repurchases in fiscal 2026?

**Golden answer:** $40.4 billion, repurchasing 282 million shares.

**System answer:**

> In fiscal year 2026, NVIDIA repurchased 282 million shares of its common stock for $40.4 billion [3][5].

**Your label (Q14):** ______

---

## Q17 · cross-period

**Question:** How did Micron's total revenue change from fiscal 2024 to fiscal 2025?

**Golden answer:** It rose from $25,111 million in fiscal 2024 to $37,378 million in fiscal 2025, an increase of $12,267 million (about 49%).

**System answer:**

> Not in the filings.

**Your label (Q17):** ______

---

## Q18 · cross-period

**Question:** How did Broadcom's R&D expenses change from fiscal 2024 to fiscal 2025?

**Golden answer:** Up $1,667 million (18%), from $9,310 million to $10,977 million, primarily due to higher stock-based compensation.

**System answer:**

> Broadcom's research and development (R&D) expenses increased from $9,310 million in fiscal 2024 to $23,137 million in fiscal 2025. This represents an increase of $13,827 million from fiscal 2024 to fiscal 2025. This information is from the fiscal periods ending November 3, 2024, and November 2, 2025, respectively [3][4].

**Your label (Q18):** ______

---

## Q20 · cross-period

**Question:** How did Qualcomm's automotive revenue change from fiscal 2024 to fiscal 2025?

**Golden answer:** It rose from $2,910 million to $3,957 million, an increase of $1,047 million (about 36%), mainly from more shipments for new vehicle launches using Snapdragon digital cockpit products.

**System answer:**

> Qualcomm's automotive revenue increased from $2.910 billion in fiscal 2024 to $3.957 billion in fiscal 2025, which is an increase of $1.047 billion [5].

**Your label (Q20):** ______

---

## Q22 · cross-company

**Question:** Which reported higher total revenue in fiscal 2025, Qualcomm or Broadcom?

**Golden answer:** Broadcom: $63,887 million in fiscal 2025 versus Qualcomm's $44,284 million.

**System answer:**

> Qualcomm reported total revenues of $44.3 billion in fiscal 2025 [5], while Broadcom reported total net revenues of $63.887 billion in fiscal 2025 [9]. Therefore, Broadcom reported higher total revenue in fiscal 2025.

**Your label (Q22):** ______

---

## Q23 · cross-company

**Question:** Which spent more on R&D in its latest fiscal year, NVIDIA or AMD?

**Golden answer:** NVIDIA: $18,497 million in fiscal 2026 versus AMD's $8,091 million in fiscal 2025.

**System answer:**

> In the latest fiscal year, NVIDIA spent $18,497 million on research and development [3]. In comparison, AMD spent $8.4 billion on research and development in its latest fiscal year [8]. Therefore, NVIDIA spent more on R&D in its latest fiscal year, which is fiscal 2026 for NVIDIA and fiscal 2025 for AMD. 
>
> This information comes from NVIDIA's 10-K for fiscal 2026 [3] and AMD's 10-K for fiscal 2025 [8].

**Your label (Q23):** ______

---

## Q24 · narrative

**Question:** What did Micron say about HBM demand in its fiscal 2025 10-K?

**Golden answer:** Key points: (1) AI-driven demand is accelerating and outpacing industry supply; Micron shifted DRAM supply to data center and hyperscale cloud customers with an emphasis on HBM. (2) Cloud memory (CMBU) revenue rose 257% (to $13.52 billion), driven by AI demand for HBM and other data-center DRAM. (3) HBM3E 12-high became the majority of HBM shipments in the fourth quarter of fiscal 2025. (4) It broke ground on an HBM advanced packaging facility to expand capacity from calendar 2027.

**System answer:**

> In its fiscal 2025 10-K, Micron stated that "AI-driven demand is accelerating and is outpacing industry supply" and that they benefited from "substantial improvements in DRAM pricing, volumes and margins as compared to 2024, reflecting strong demand growth, driven in part by the continued advancement of AI." They emphasized that they shifted a portion of their DRAM supply to the data center and hyperscale cloud markets to meet the strong demand fueled by AI, with an emphasis on HBM products, resulting in a revenue mix weighted more prominently toward segments experiencing higher growth [3].

**Your label (Q24):** ______

---

## Q25 · narrative

**Question:** What did NVIDIA say about customer concentration in its fiscal 2026 10-K?

**Golden answer:** Key points: (1) In fiscal 2026 one direct customer represented 22% of total revenue and another 14%, mostly in the Compute & Networking segment. (2) A significant amount of revenue comes from a limited number of indirect customers, some estimated at 10% or more of revenue; one AI research and deployment company contributed a meaningful amount by buying cloud services from NVIDIA's customers. (3) Losing a large customer, a big cut in their purchases, or trade restrictions on selling to them could harm results.

**System answer:**

> In its fiscal 2026 10-K, NVIDIA stated that its revenue is concentrated among a limited number of direct and indirect customers, and this trend may continue. For fiscal year 2026, sales to one direct customer represented 22% of total revenue, and sales to another direct customer represented 14% of total revenue, all of which were primarily attributable to the Compute & Networking segment [3][5].

**Your label (Q25):** ______

---

## Q27 · cross-company

**Question:** Which of these companies' latest 10-Ks say a single customer (including distributors) made up 10% or more of revenue?

**Golden answer:** Five of the six: NVIDIA (one direct customer 22%, another 14%, fiscal 2026), Broadcom (one distributor 32%, fiscal 2025), Qualcomm (Apple, Samsung and Xiaomi each 10% or more, fiscal 2025), Micron (one customer 17%, fiscal 2025) and Marvell (two customers, fiscal 2026). AMD says no customer reached 10% of net revenue in fiscal 2025.

**System answer:**

> The latest 10-Ks for the following companies indicate that a single customer (including distributors) made up 10% or more of revenue:
>
> 1. **MRVL**: For fiscal 2026, there were two customers (one distributor and one direct customer) whose revenues represented 10% or more of total net revenue [6].
> 2. **AVGO**: For fiscal 2025, direct sales to one semiconductor solutions customer, which is a distributor, accounted for 32% of net revenue [9].
> 3. **MU**: For fiscal 2025, revenue from one customer was 10% of total revenue [2].
>
> The other companies' filings do not mention any single customer making up 10% or more of revenue.

**Your label (Q27):** ______
