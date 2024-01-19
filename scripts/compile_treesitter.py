from glob import glob
from tree_sitter import Language

languages = glob("tree-sitter-*")


Language.build_library(
    "unstructured/treesitter_build/languages.so",
    languages
)

