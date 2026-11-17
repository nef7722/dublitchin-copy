#!/bin/bash
# local test wrapper imitating the publish skeleton
cd "$(dirname "$0")/tour"
{ echo '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style></head><body>'; cat index.html; echo '</body></html>'; } > test.html
