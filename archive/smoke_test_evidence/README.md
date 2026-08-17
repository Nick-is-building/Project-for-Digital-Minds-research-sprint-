# Smoke test evidence

`smoke_raw.prefix.jsonl` is the raw call log from the first smoke test, before the
thinking-block fix.

It supports the claim in Appendix D that 52 of 128 rating calls to
`claude-opus-5` failed with `AttributeError("'ThinkingBlock' object has no
attribute 'text'")`. Count the failures directly:

```
grep -c "ThinkingBlock" smoke_raw.prefix.jsonl
```

The fix was to scan for the first text block instead of indexing block 0, and
to disable thinking explicitly on rating calls. See DEVLOG.md, 2026-08-15
05:20, and Appendix D of the paper.
