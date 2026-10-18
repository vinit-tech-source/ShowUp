# Messaging LLM Evaluation Report: `llama3.2:3b`

- **Date**: 2026-10-18 20:30:49
- **Model**: `llama3.2:3b`
- **Total Scenarios Evaluated**: 5
- **Perfect Compliance Rate (All Checks Passed)**: **100.0%** (5/5)

## Guardrail Pass Rates

| Guardrail Check | Passed | Total | Pass Rate |
| :--- | :---: | :---: | :---: |
| Client Name Present | 5 | 5 | **100.0%** |
| Appointment Time Present | 5 | 5 | **100.0%** |
| Service/Business Context Present | 5 | 5 | **100.0%** |
| Word Count Limit (<= 40 words) | 5 | 5 | **100.0%** |
| Zero Guilt / Blame Words | 5 | 5 | **100.0%** |
| No Invented Facts (Price/Address/Promo) | 5 | 5 | **100.0%** |
| Polite Professional Tone | 5 | 5 | **100.0%** |

## Evaluated Samples & Failures

### All samples passed 100% of guardrails! 🎉

### Sample Passing Output

- **Scenario**: First-time customer | Luxe Salon (Haircut & Styling) | Dan Cole | Today at 4:30 PM
  - *Draft (24 words)*: "Hi Dan, just a friendly reminder that you have a Haircut & Styling appointment today at 4:30 PM. Looking forward to seeing you then!"
- **Scenario**: First-time customer | Luxe Salon (Haircut & Styling) | Dan Cole | Tomorrow at 10:00 AM
  - *Draft (24 words)*: "Hi Dan, just a friendly reminder that you're booked for a Haircut & Styling tomorrow at 10:00 AM. Looking forward to seeing you then!"
- **Scenario**: First-time customer | Luxe Salon (Haircut & Styling) | Dan Cole | Thursday at 2:00 PM
  - *Draft (27 words)*: "Hi Dan, just a friendly reminder that you have a Haircut & Styling appointment scheduled for this Thursday at 2:00 PM. Looking forward to seeing you then!"