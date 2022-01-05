# Changelog

## [0.4.0] 05-01-2022


### NEW:

- You can now choose to pass global options to sub commands or not by .
 The default is that: 
  - if a processor is passed, we don't pass the options
  - otherwise, we follow the value of `propagate_options`
