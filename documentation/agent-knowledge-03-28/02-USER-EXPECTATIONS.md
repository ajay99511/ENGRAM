# User Expectations & Preferences

**Last Updated:** March 27, 2026  
**User Profile:** Personal AI Assistant Builder

---

## 👤 User Identity

**Role:** Builder of local-first personal AI assistant system  
**Vision:** Production-grade system that runs entirely on user's machine  
**Timeline:** Building through 2026  
**Current Goal:** Complete implementation, ready for production use

---

## 🎯 Working Style Preferences

### Quality Expectations

**HIGH PRIORITY:**
- ✅ **Production-grade code** - Well-structured, documented, tested
- ✅ **Security-first** - Secret redaction, audit logging, permission checks
- ✅ **Performance** - Efficient token usage, optimized context management
- ✅ **Transparency** - User should see system status (health dashboard, audit logs)
- ✅ **Local-first** - Run on user's machine, privacy-preserving

**MEDIUM PRIORITY:**
- ⚠️ **Test coverage** - Target 80%+ (currently 79%)
- ⚠️ **Documentation** - Comprehensive but concise (no code dumps)

**LOW PRIORITY:**
- ⏳ **Perfect completion** - Ship at 98% if remaining is optional

### Communication Preferences

**DO:**
- ✅ Provide clear, structured information
- ✅ Reference documents by path (don't paste code)
- ✅ Explain rationale, not just what
- ✅ Flag production-blocking vs optional issues
- ✅ Use research-backed approaches (cite sources)

**DON'T:**
- ❌ Paste large code blocks without explanation
- ❌ Make assumptions without validating
- ❌ Hide limitations or trade-offs
- ❌ Use marketing language ("top 1%") - be factual

### Decision-Making Style

**Preferred Approach:**
1. Present options with trade-offs
2. Recommend based on facts/performance/efficiency
3. Let user make final decision
4. Document decision rationale

**Example:**
```
Option A: ARQ (simpler, asyncio-native)
Option B: Celery (more mature, complex)
Recommendation: ARQ with Celery fallback documented
Rationale: Matches FastAPI async patterns, 2-3 day migration path if needed
```

---

## 🏗️ Technical Preferences

### Architecture Principles

**Strongly Preferred:**
- ✅ Modular design (easy to enhance/maintain)
- ✅ Industry best practices (research-backed)
- ✅ Clear separation of concerns
- ✅ Graceful error handling
- ✅ Observability (health checks, audit logs)

**Avoid:**
- ❌ Over-engineering (YAGNI principle)
- ❌ Premature optimization
- ❌ Vendor lock-in (prefer open standards)

### Technology Choices

**Preferred Stack:**
- **Backend:** Python FastAPI (AI/ML ecosystem)
- **Frontend:** React + TypeScript + Tauri
- **Database:** Qdrant (vector), SQLite (relational), Redis (cache)
- **Local LLM:** Ollama
- **Memory:** Mem0 + custom 5-layer system

**Decision Criteria:**
1. Performance (benchmarks when available)
2. Community support (active maintenance)
3. Documentation quality
4. Learning curve (prefer established patterns)

---

## 📊 Quality Metrics

### Code Quality

**Targets:**
- Test coverage: 80%+ (currently 79%)
- Documentation: 100% of public APIs
- Type hints: 100% (Python), strict (TypeScript)
- Linting: No errors, minimal warnings

**Acceptable Trade-offs:**
- 79% coverage if remaining tests are edge cases
- 98% completion if remaining is optional enhancement

### Documentation Quality

**Requirements:**
- ✅ No code dumps (reference file paths)
- ✅ Explain what + why + where
- ✅ Keep updated (timestamp all changes)
- ✅ Structured for quick retrieval

**Preferred Format:**
- Markdown with clear hierarchy
- Tables for comparisons
- Code blocks only for configuration/examples
- Cross-references between documents

---

## 🎯 Success Criteria

### For This Project

**Must Have:**
- ✅ All core features implemented
- ✅ Production-ready (no critical bugs)
- ✅ Comprehensive documentation
- ✅ Health monitoring
- ✅ Security features (redaction, audit, permissions)

**Nice to Have:**
- ⚠️ 80%+ test coverage
- ⚠️ All optional enhancements

**Definition of Done:**
- Core features complete ✅
- Documentation complete ✅
- Health monitoring working ✅
- Test coverage acceptable (79% ≈ 80%) ✅
- **Ship at 98%** ✅

---

## 🔄 Feedback Style

**Preferred:**
- Direct, honest assessment
- Data-driven (metrics when possible)
- Solution-oriented (problems + fixes)
- Timely (flag issues immediately)

**Example:**
```
❌ "This might not work but..."
✅ "Issue: Route ordering conflict. Impact: /jobs/stats returns wrong data. Fix: Reorder routes (see PR #123)"
```

---

## 📚 Related Documents

- **Onboarding:** `00-AGENT-ONBOARDING.md`
- **Project State:** `01-PROJECT-STATE.md`
- **Architecture:** `03-ARCHITECTURE-DECISIONS.md`
- **File Manifest:** `04-FILE-MANIFEST.md`

---

**Last Review:** March 27, 2026  
**Next Review:** After production deployment  
**Status:** ✅ CURRENT
