supported_languages="go javascript python"

for language in $supported_languages; do 
  git clone https://github.com/tree-sitter/tree-sitter-"$language"
done

python scripts/compile_treesitter.py

for language in $supported_languages; do 
  rm -rf tree-sitter-"$language"
done

