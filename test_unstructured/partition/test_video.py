# pyright: reportPrivateUsage=false

"""Test-suite for the `unstructured.partition.audio` module."""

from unstructured.partition.video import (
    partition_video
)

def test_partition_audio_from_filename():
    elements = partition_video("example-docs/video/wh-bees.mp4")
    assert len(elements) == 10
    # Example full output:
#     [{'element_id': '4a6956512755bf0db4cca8184fe4d8d4',
#   'metadata': {'end_time': 47.445,
#                'file_directory': 'example-docs/video',
#                'filename': 'wh-bees.mp4',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 14.684999},
#   'text': 'When we first got into the White House, I met Charlie who was '
#           'telling me about, the bees, that he kept at his house. It really '
#           'came together fast from there, and we got it in here in late March, '
#           "and it's been doing good ever since. Curators have told me as well "
#           "that they researched it somewhat, and they can't find any evidence "
#           "of a hive here in the past. So, yeah, it's pretty cool to have the "
#           'first one here for sure. You know, bees are obviously essential to '
#           'the process of growing food, being key pollinators.',
#   'type': 'TranscriptFragment'},
#  {'element_id': 'dccb6f32c9e631e7241888dc57f4c017',
#   'metadata': {'end_time': 47.445,
#                'file_directory': 'example-docs/video',
#                'filename': 'wh-bees.mp4',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 0},
#   'text': 'The White House has a beehive. The bees are being tended to by a '
#           'beekeeper. The chef is excited about the honey. ',
#   'type': 'VideoFragmentCaption'},
#  {'element_id': 'a03dc94bf8314ececb139d75f63fb366',
#   'metadata': {'end_time': 86.755,
#                'file_directory': 'example-docs/video',
#                'filename': 'wh-bees.mp4',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 47.445},
#   'text': 'And so for kids who are coming, to visit the garden to learn about '
#           'these topics, it was a great opportunity to show them the whole the '
#           'whole cycle and process. So the day we harvested was just a a '
#           'wonderful day and really exciting. Charlie started off by smoking '
#           'the bees out, which is, you know, old school. When you put a couple '
#           'puffs of smoke here at the entrance of the hive, it causes the '
#           'guard bees to not be able to communicate as well because a lot of '
#           'the communication in the hive is by the sense of smell. I mean, '
#           "there there's something a little disconcerting about, you know, "
#           'being surrounded by thousands and thousands of bees.',
#   'type': 'TranscriptFragment'},
#  {'element_id': '634ece1e165d3fc6e8840c80323a9d4d',
#   'metadata': {'end_time': 86.755,
#                'file_directory': 'example-docs/video',
#                'filename': 'wh-bees.mp4',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 47.445},
#   'text': 'The White House has bees and a garden.  A group of children are '
#           'visiting the White House garden to learn about the garden and the '
#           'beehive.  The bees are smoked out of their hive to inspect the '
#           'hive. ',
#   'type': 'VideoFragmentCaption'},
#  {'element_id': 'd615a17e10eb7925c74f6661963977aa',
#   'metadata': {'end_time': 109.30499,
#                'file_directory': 'example-docs/video',
#                'filename': 'wh-bees.mp4',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 86.815},
#   'text': 'There are probably at least 70,000 bees in this hive. He pulled he '
#           'pulled out each tray of of of cone and they blew off all the bees '
#           'from each tray. You just blow them on out of there and they fly on '
#           'back up into the hive. The first harvest we did last year, we did '
#           'it pretty early. We pulled out 12 capped frames and then brought '
#           'that into the White House.',
#   'type': 'TranscriptFragment'},
#  {'element_id': '28ed8006352aa76e7720bbda2b7af023',
#   'metadata': {'end_time': 109.30499,
#                'file_directory': 'example-docs/video',
#                'filename': 'wh-bees.mp4',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 86.755},
#   'text': 'The video shows people harvesting honey from a beehive. They use a '
#           'leaf blower to blow bees off the frames and then remove the frames '
#           'from the hive. They are preparing to bring the honey into the White '
#           'House. ',
#   'type': 'VideoFragmentCaption'},
#  {'element_id': '4824d1948f553579568815fc84b8e37d',
#   'metadata': {'end_time': 132.855,
#                'file_directory': 'example-docs/video',
#                'filename': 'wh-bees.mp4',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 109.30499},
#   'text': 'And when we got in here, just cut open the comb, just the very top '
#           'layer. He puts it in in this machine that with a hand crank, you '
#           'spin really fast. And uses centrifugal force to sling the honey out '
#           'of the cells. So we went ahead, we extracted that way. And you end '
#           'up having like a big old bucket of honey.',
#   'type': 'TranscriptFragment'},
#  {'element_id': '5b8ef3ef7c9d8677f6eb0b8007aa1ef4',
#   'metadata': {'end_time': 132.855,
#                'file_directory': 'example-docs/video',
#                'filename': 'wh-bees.mp4',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 109.30499},
#   'text': 'The video shows a man extracting honey from a beehive. He uses a '
#           'centrifuge to spin the honey out of the honeycomb. The honey is '
#           'then collected in a bucket. \n',
#   'type': 'VideoFragmentCaption'},
#  {'element_id': 'e43dc7f60970b06903a8cf8758aec42f',
#   'metadata': {'end_time': 144.4295,
#                'file_directory': 'example-docs/video',
#                'filename': 'wh-bees.mp4',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 132.995},
#   'text': 'We go ahead and let it settle for at least a week. I like to get it '
#           "nice and clear. Then after that's been done, it's ready to put into "
#           'bottles, containers, whatever size you wanna do.',
#   'type': 'TranscriptFragment'},
#  {'element_id': '8cca9cb536c1e17de90f839c63d356ca',
#   'metadata': {'end_time': 144.4295,
#                'file_directory': 'example-docs/video',
#                'filename': 'wh-bees.mp4',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 132.855},
#   'text': 'The video shows a man harvesting honey from his beehives. He first '
#           'drains the honey from the extractor and then bottles it. ',
#   'type': 'VideoFragmentCaption'}]
