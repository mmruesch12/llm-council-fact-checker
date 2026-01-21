### Don'ts ❌

- **Don't use only one provider** - Reduces diversity of perspectives
- **Don't skip fact-checking** - Core value proposition of the system
- **Don't hide agent identities** - Transparency builds trust
- **Don't fail on single agent failure** - System should degrade gracefully
- **Don't ignore parsing failures** - Implement fallback extraction
- **Don't hardcode model names in prompts** - Keep agents model-agnostic
- **Don't expose API keys** - Use environment variables only
- **Don't skip de-anonymization** - Users should see which models said what

---

## Conclusion

The LLM Council agent architecture demonstrates that **collective intelligence** can exceed individual model capabilities through:

1. **Structured deliberation** across four distinct stages
2. **Anonymized peer review** to eliminate bias
3. **Fact-checking layer** for accuracy verification
4. **Transparent validation** for user trust

By following the guidelines in this document, developers can effectively configure, deploy, and extend the council system for diverse use cases while maintaining the core principles of factual accuracy, transparency, and collaborative intelligence.

For technical implementation details, see [CLAUDE.md](CLAUDE.md).

For API usage and integration examples, see [SYNTHESIZE_API.md](SYNTHESIZE_API.md).

For security best practices, see [API_SECURITY.md](API_SECURITY.md).
