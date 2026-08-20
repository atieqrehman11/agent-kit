# Instructions

TODO: how Genie should answer — tone, preferred joins and filters, business
definitions, units, and the caveats a reader needs to trust a number.
Multi-paragraph prose is fine.

`python/build_space.py` sends this file **byte-verbatim** as the space's text
instructions. Nothing is stripped, reflowed or normalised: the payload is
compared byte for byte on the next deploy, so tidying this file turns a no-op
deploy into a content change. `.editorconfig` stops your editor adding a trailing
newline for the same reason.

The catalog and schema placeholders are substituted per environment in this file
too, so you can name a table here without pinning it to one workspace. Write them
the same way `src/data_sources.yml` does.
