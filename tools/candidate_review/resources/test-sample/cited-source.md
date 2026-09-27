# Sample source cited by the review tests

This file exists only to be cited. The candidate review tests build small
catalogues whose items cite files of this repository at a pinned revision,
and the native review reader refuses a catalogue once a cited file in the
working tree differs from the bytes pinned for it.

Until September 27, 2026 the tests cited
src/loop_engine/core/service_runtime/catalogue_packages.py, a production
module, so every change to that module broke them. They cite this file
instead, pinned at the newest commit that changed this file or LICENSE
(tools/review_sample_source.py). Nothing reads these words; only the bytes
are compared. A committed edit moves the pin with it, and an uncommitted
edit makes the reader refuse the test catalogues, as it should.
