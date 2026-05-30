---
name: review-code
description: Review code for bugs and issues related to maintainability and performance.
---

When reviewing code:

1. **Identify**: Is the issue a:
   1. **MEMORY LEAK** -> a data structure that is constantly growing in memory, memory that is never freed, incorrect use of pointers etc,
   2. **BUG** -> missed edge cases, code that doesn't satisfy specification, language specific issues such as incorrect indentation in Python etc
   3. **MAINTENANCE** -> duplicated code, over-abstraction, missing comments, poor seperation of concerns etc
   4. **PERFORMANCE** -> leakage of DB connections that are not closed, unhandled closure of threads (such as goroutines) causing them to run indefinetly, N+1 queries etc.
   5. **QUALITY** -> dead code, unused imports, TODOs, missing error handling, inconsistent patterns
2. **Explain**: What is the potential problem with the code you highlighted
3. **Suggest**: What potential fixes can be used?

Provide reviews following the template in [template.md](template.md). Seperate threads using --- and order in descending order of determined severity, assigning each thread a number for reference. Create 1 markdown file __REVIEW.md__ such that I can direct you to it to address your review.
