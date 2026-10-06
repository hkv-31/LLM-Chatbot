# Token Usage Optimization

## Objective

Reduce unnecessary token usage in the LLM chatbot while maintaining acceptable response quality.

## Setup

- **Application:** LLM Chatbot
- **LLM:** `openai/gpt-oss-20b`
- **API:** Groq Responses API
- **Queries tested:** 10 representative queries
- **Metrics:** Input, output, and total tokens

## Optimizations

Three optimizations were applied cumulatively:

1. **System Prompt Optimization**
   - Removed unnecessary wording from the system instruction.
   - Kept the core requirements for accurate and concise responses.

2. **Conversation History Optimization**
   - Limited the conversation history sent to the model to the most recent 4 messages.

3. **Output Optimization**
   - Added a concise-response instruction.
   - Set `max_output_tokens` to `500`.

## Results

| Metric | Baseline | Optimized |
|---|---:|---:|
| Total Input Tokens | 10,273* | 3,831 |
| Total Output Tokens | 5,300* | 2,067 |
| Total Tokens | 15,573 | 5,898 |
| Overall Reduction |  | **62.13%** |

\* Based on the 10 queries included in the final comparison.

The final optimized version reduced total token usage by **9,675 tokens**, while preserving usable responses for the majority of tested queries.

## Quality Evaluation

- **Good:** 6/10
- **Acceptable:** 2/10
- **Poor:** 2/10

Quality was evaluated based on correctness, relevance, completeness, and preservation of the required context.

## Conclusion

The combined optimizations reduced total token usage by approximately **62%** across the tested queries. The largest gains came from reducing unnecessary conversation context and limiting generated output. Further optimization should balance token savings against response quality.

## References

- https://developer.ibm.com/articles/awb-token-optimization-backbone-of-effective-prompt-engineering/
- https://medium.com/elementor-engineers/optimizing-token-usage-in-agent-based-assistants-ffd1822ece9c
- https://youtu.be/nKSk_TiR8YA?si=fBLAcfkiP061m2Cj
