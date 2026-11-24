#!/bin/sh
set -e
if [ "$BUGS" = "1" ]; then
  cat /opt/extra/compact.css >> /usr/share/nginx/html/style.css
fi
