from tools.nvda_tool import NVDATextExtractor
from tools.nvda_filter import NVDAFilter
from tools.nvda_parser import NVDAParser
from tools.nvda_classifier import NVDAClassifier
import time
import json

extractor = NVDATextExtractor()
filter = NVDAFilter()
parser = NVDAParser()
classifier = NVDAClassifier()

with open("nvda_log.txt", "w", encoding="utf-8") as log:

    print("Listening...")

    while True:

        text = extractor.get_new_text()

        if text:

            cleaned = filter.clean(text)

            events = parser.parse(cleaned)
            
            classifier.classify(events)
            classifier.save()


            for event in events:
                print("=" * 50)
                print(event)

                log.write(json.dumps({
                    "role": event.role,
                    "name": event.name,
                    "value": event.value,
                    "description": event.description,
                    "level": event.level,
                    "attributes": event.attributes
                }, ensure_ascii=False))
                log.write("\n")

            log.flush()

        time.sleep(0.2)
        
        