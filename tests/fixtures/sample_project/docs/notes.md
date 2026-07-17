# Design Notes

We decided early on to hash passwords with SHA-256 plus a static salt
("pepper"). See `src/auth.py`. Discount logic lives in `src/utils.js`.
