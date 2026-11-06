# Nuclei Detection Techniques (method index)

Derived from 13,777 local nuclei templates. Grouped by class; shows the
matcher kinds each class relies on (what to check), not the templates themselves.

| Class | Templates | Top matcher kinds | Severity mix |
|---|---:|---|---|
| exposure | 3202 | word×3051, status×1376, dsl×1230, negative×249, regex×201 | info:906, high:867, medium:812, low:440 |
| other | 2699 | word×5504, dsl×2962, status×1345, regex×822, binary×114 | info:2168, high:190, medium:90, low:23 |
| auth-bypass | 1751 | word×1594, dsl×1182, status×1168, regex×92, negative×33 | info:1086, high:391, critical:220, medium:44 |
| xss | 1453 | word×1890, dsl×1608, status×764, regex×43, negative×13 | medium:1270, high:152, critical:20, low:7 |
| rce | 1220 | dsl×1366, word×1136, status×561, regex×261, negative×29 | critical:816, high:203, info:110, medium:76 |
| lfi | 917 | status×666, regex×517, dsl×514, word×466, negative×7 | high:587, medium:193, critical:127, info:5 |
| sqli | 618 | dsl×1024, word×370, status×194, regex×27, negative×13 | critical:369, high:228, medium:20, info:1 |
| cve | 595 | dsl×654, word×425, status×239, regex×154, negative×14 | medium:233, critical:199, high:160, low:3 |
| panels | 514 | word×459, status×361, dsl×166, regex×29, xpath×2 | info:489, medium:10, high:6, unknown:1 |
| cms | 252 | dsl×125658, regex×191, word×64, status×45 | info:234, high:5, low:4, medium:3 |
| ssrf | 204 | word×233, dsl×196, status×60, regex×19 | high:98, critical:50, medium:49, info:6 |
| cloud | 105 | word×76, dsl×56, status×47, negative×10, regex×3 | info:70, medium:18, high:8, critical:5 |
| takeover | 80 | dsl×156, word×86, status×13, negative×5, regex×4 | high:73, info:3, medium:1, low:1 |
| redirect | 44 | regex×36, dsl×16, status×12, word×7 | medium:32, low:6, info:4, unknown:1 |
| upload | 36 | dsl×36, word×23, status×11, regex×2 | critical:23, high:8, info:3, medium:2 |
| ssti | 35 | dsl×56, regex×11, word×6, status×3, negative×1 | high:23, info:9, medium:2, critical:1 |
| graphql | 22 | word×32, status×21, negative×10, dsl×2, regex×1 | info:22 |
| misconfig | 14 | dsl×18, word×9, status×4, binary×2, regex×1 | info:8, low:4, medium:1, high:1 |
| crlf | 7 | word×4, dsl×4, regex×2, status×2 | low:5, info:2 |
| xxe | 7 | word×11, dsl×4, regex×2, status×1 | high:6, medium:1 |
| deserialization | 2 | word×2, dsl×2, status×1 | high:2 |

## How to use

For the class you're testing, the matcher kinds tell you the *observable* the check keys on:
status codes, response words, regex, `dsl` expressions (boolean logic over response),
binary/`size` (blob detection), `xpath`/`json` (structured extraction).
Mirror that observable when building your own PoC or scanner rule.

