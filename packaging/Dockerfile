FROM alpine:3.18\nRUN apk add --no-cache curl jq\nCOPY publisher /usr/local/bin/publisher\nRUN chmod +x /usr/local/bin/publisher\nENTRYPOINT [/usr/local/bin/publisher]
