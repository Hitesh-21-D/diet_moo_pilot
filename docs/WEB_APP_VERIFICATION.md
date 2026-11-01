# Web application verification

Verified on 31 October 2026 using native PostgreSQL 17.11, without Docker.

- API tests: 6 passed (authentication, CSRF, ownership, validation, immutable per-day snapshots, cancellation/recovery, comparative statistics and exports).
- Frontend tests: 3 passed (day-specific input/output matching and honest no-feasible results).
- TypeScript and production Vite build passed. Plotly lazy-bundle size warning and a TestClient deprecation warning remain non-blocking.
- Browser: sign-in, two-day food entry/duplication/portion edits/save, recommendation rendering, APPO diagnostics, comparative metrics and CSV download verified. Desktop and 390px mobile layouts inspected; no browser console errors.
- Real worker integration: seven jobs completed; every returned solution passed all 33 constraints.

| Input day | Algorithm | Status | Actual evaluations | Feasible Pareto diets |
| --- | --- | --- | ---: | ---: |
| Validation day 1 | APPO | completed | 15000 | 57 |
| Validation day 1 | MOEA/D | completed | 14952 | 27 |
| Validation day 1 | MOPSO | completed | 15000 | 92 |
| Validation day 1 | NSGA-II | completed | 15000 | 95 |
| Validation day 1 | NSGA-III | completed | 15000 | 16 |
| Validation day 1 | SPEA2 | completed | 15000 | 100 |
| Validation day 2 | APPO | completed | 15000 | 69 |

The two input diets differ and have separate experiment IDs. The first day has a frozen six-algorithm comparison; the APPO-only second day correctly omits comparative HV/IGD/PETQ. JSON experiment and representative-diet CSV exports passed.

This is functional validation on the pilot profile with seed 42, not evidence that APPO outperforms all baselines or that every new profile admits a feasible diet. The earlier development run interrupted by a schema migration remains labelled failed/cancelled in the validation account; it was excluded from this clean verification.

See WEB_APP.md for usage, the free technology stack, reproducibility policies and limitations.

Clean restart check passed: all seven completed results, sessions and comparative CSV remained available after stopping and restarting PostgreSQL, API and worker.

## Usability update — 31 October 2026

Replaced the search-plus-dropdown food form with a direct searchable food list, portion steppers and automatic portion-field focus after adding. Saving selects the saved input days. Research settings are collapsed for everyday use. Recommendation KPIs now show energy, protein and fibre against personal targets, plus the number of changed food entries. The comparison shows per-food Keep/Add/Remove/Adjust portion actions, current and suggested portions, a changes-only filter, and current/suggested/target nutrient totals.

Validation: six frontend tests passed, TypeScript and Vite production build passed, and browser checks verified direct adding, portion editing, saving/automatic day selection, comparison rendering and changes-only filtering. Responsive meal cards were inspected at 390px without page overflow. No optimizer or database changes were required for this update.

## AmritAHARA layout update — 31 October 2026

Meal cards now share a fixed height with internal scrolling for long lists. Food search uses a fixed-size native modal dialog with keyboard focus and Escape dismissal. Browser measurement confirmed all four desktop cards are 400px high; card coordinates and dialog bounds were unchanged when filtering from all foods to two matches. Recommendations now show complete current and suggested meals in paired columns without Keep/Add/Remove labels. Public interface branding and browser title are AmritAHARA; existing account/session identifiers remain compatible. New Start-AmritAHARA.ps1 and Stop-AmritAHARA.ps1 wrappers retain the existing launcher behavior. Six frontend tests passed, including dialog focus and full-diet rendering.
