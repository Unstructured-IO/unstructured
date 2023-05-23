
function join_by {
  local d=${1-} f=${2-}
  if shift 2; then
    printf %s "$f" "${@/#/$d}"
  fi
}

excludefiles=("requirements/build.txt")

shopt -s nullglob
reqfiles=(requirements/*.txt)

for excludefile in ${excludefiles[@]}
do
    reqfiles=( "${reqfiles[@]/$excludefile}" )
done

echo "${reqfiles[@]}"
reqstring="-r $(join_by ' -r ' ${reqfiles[@]})"

pipcommand="pip install --dry-run --ignore-installed ${reqstring}"
$pipcommand