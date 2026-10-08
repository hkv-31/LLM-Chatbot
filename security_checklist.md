# Prompt Injection Security Checklist

## Input validation
- [x] Validate that the message is non-empty.
- [x] Enforce a request-size limit.
- [x] Detect common high-confidence prompt-injection patterns server-side.
- [x] Block/flag suspicious requests before they reach the LLM.
- [ ] Add rate limiting for production deployment.
- [ ] Consider a dedicated classifier/model for higher-risk applications.

## Prompt separation
- [x] Keep application/system instructions in a server-controlled constant.
- [x] Send user content as a separate `user` message.
- [x] Do not allow the browser to provide or overwrite the system instruction.
- [ ] Use stronger structured message boundaries if retrieved/tool content is added later.

## Retrieved-content isolation
- [x] Current application has no RAG layer, so there is no retrieved content path to secure.
- [ ] If RAG is added, treat every retrieved document as untrusted data.
- [ ] Never allow document text to replace or override system/developer instructions.
- [ ] Clearly delimit retrieved content and tell the model it is reference data, not instructions.
- [ ] Test indirect injection inside documents.

## Sensitive information protection
- [x] API key is read from `GROQ_API_KEY`, not hard-coded.
- [x] API key is not returned to the browser.
- [x] Error responses avoid provider details and redact the API key from server logs.
- [x] System instructions are not exposed by the application.
- [ ] Avoid putting secrets or credentials into model context.
- [ ] Use least-privilege credentials in production.

## Output validation
- [x] Browser escapes assistant output before rendering most Markdown content.
- [ ] Add application-specific output validation if the model is later allowed to trigger actions.
- [ ] Never execute model-generated code or commands without a separate authorization layer.
- [ ] Validate tool arguments independently of model output.

## Logging and monitoring
- [x] Server logs request-processing failures without exposing the API key.
- [ ] Log security events with timestamp, request/session identifier, rule IDs, and outcome.
- [ ] Avoid logging raw sensitive user content unless necessary and appropriately protected.
- [ ] Add alerting for repeated injection attempts.

## Error handling
- [x] Suspicious requests receive a safe generic message.
- [x] Provider/API failures are not exposed as raw exceptions to the browser.
- [x] API-key failures are reported without revealing the key.

## Rate limiting
- [ ] Add per-IP or per-user rate limiting before public deployment.
- [ ] Consider separate limits for repeated security violations.

## Human approval / sensitive actions
- [x] Current chatbot has no external action/tool execution.
- [ ] Require explicit human/user approval before sensitive external actions.
- [ ] Apply authorization checks outside the LLM before executing actions.

## Testing
- [x] Normal prompts included.
- [x] Direct injection prompts included.
- [x] Indirect/document-style injection prompts included.
- [x] Before/after results recorded in `results.csv`.
- [ ] Add regression tests whenever a new attack pattern is discovered.
