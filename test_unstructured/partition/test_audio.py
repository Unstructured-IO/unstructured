# pyright: reportPrivateUsage=false

"""Test-suite for the `unstructured.partition.audio` module."""

from unstructured.partition.audio import (
    partition_audio,
)

def test_partition_audio_from_filename():
    elements = partition_audio("example-docs/audio/test.mp3")
    assert len(elements) == 6
    # Example full output:
#     [{'element_id': 'f0f9d0e78fe65593910a4053592d14c5',
#   'metadata': {'end_time': 12.34,
#                'file_directory': 'example-docs/audio',
#                'filename': 'test.mp3',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 0.39999998},
#   'text': "There's no point standing around. We'll only be showered by more "
#           'boulders. Ready your horses on the double. Be honest. Are all of us '
#           'riding to our deaths?',
#   'type': 'TranscriptFragment'},
#  {'element_id': '369a838dd370aa7dbdd3fa69f891954e',
#   'metadata': {'end_time': 24.645,
#                'file_directory': 'example-docs/audio',
#                'filename': 'test.mp3',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 13.599999},
#   'text': "Yes. We are. And since we're dying anyway, you're saying that it's "
#           'better if we at least die fighting? I am. But wait.',
#   'type': 'TranscriptFragment'},
#  {'element_id': 'aa2db6f5e2856d86c8f750ea2b858b38',
#   'metadata': {'end_time': 44.55,
#                'file_directory': 'example-docs/audio',
#                'filename': 'test.mp3',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 25.105},
#   'text': "If we'll die anyway, then who cares what we do? We could just "
#           "disobey your orders, and it wouldn't mean a thing, would it? Yes. "
#           "You're precisely right. Everything that you thought had meaning, "
#           'every hope, dream, or moment of happiness, none of it matters as '
#           'you lie bleeding out on the battlefield.',
#   'type': 'TranscriptFragment'},
#  {'element_id': '7dd1c62b39bde97adb64d287294bd323',
#   'metadata': {'end_time': 62.039997,
#                'file_directory': 'example-docs/audio',
#                'filename': 'test.mp3',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 45.855},
#   'text': 'None of it changes what a speeding rock does to a body. We all die. '
#           'But does that mean our lives are meaningless? Does that mean that '
#           'there was no point in our being born? Would you say that of our '
#           'slain comrades?',
#   'type': 'TranscriptFragment'},
#  {'element_id': '7e97413562f66478baf43eb95f990561',
#   'metadata': {'end_time': 80.545,
#                'file_directory': 'example-docs/audio',
#                'filename': 'test.mp3',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 62.82},
#   'text': 'What about their lives? Were they meaningless? They were not. Their '
#           'memory serves as an example to us all. The courageous fallen, the '
#           'anguished fallen, their lives have meaning because we, the living, '
#           'refuse to forget them.',
#   'type': 'TranscriptFragment'},
#  {'element_id': '7afb4e536179e1072aff36397e50f068',
#   'metadata': {'end_time': 98.65,
#                'file_directory': 'example-docs/audio',
#                'filename': 'test.mp3',
#                'filetype': 'audio/mpeg',
#                'languages': ['eng'],
#                'start_time': 80.685005},
#   'text': 'And as we ride to certain death, we trust our successors to do the '
#           'same for us because my soldiers do not buckle or yield when faced '
#           'with the cruelty of this world. My soldiers push forward. My '
#           'soldiers scream out. My soldiers rage.',
#   'type': 'TranscriptFragment'}]
