#!/usr/bin/env bash
#
# check_total.sh -- find CEEX runs whose total cross-section has diverged
#                   and interactively remove them.
#
#   ./check_total.sh ~/scratch/KLOE-LA_NLO_pipig_fpi
#
# A run is flagged when either
#   * its MC error is more than ERRFAC times the median error of all runs, or
#   * its value sits more than NMAD robust sigmas (1.4826*MAD) from the median.
#
set -uo pipefail

ERRFAC=10        # -e : error blow-up factor
NMAD=5           # -n : value pull, in robust sigmas
MODE=dir         # -f : delete only the offending file instead of the run dir
ASSUME=ask       # -y : delete everything flagged, --list : never delete
PATTERN='Total cross-section'

usage() {
    cat <<USAGE
usage: $(basename "$0") [options] <run-directory>

  <run-directory>   directory holding the RUN_CEEX_* subdirectories

options:
  -e FACTOR   flag runs whose error > FACTOR * median error   (default $ERRFAC)
  -n NSIGMA   flag runs whose value is > NSIGMA robust sigmas
              from the median value                           (default $NMAD)
  -f          delete just the output file, not the whole RUN_CEEX_* directory
  -y          delete every flagged run without asking
  -l          list only, never delete
  -h          this help
USAGE
}

while getopts ":e:n:fylh" opt; do
    case $opt in
        e) ERRFAC=$OPTARG ;;
        n) NMAD=$OPTARG ;;
        f) MODE=file ;;
        y) ASSUME=yes ;;
        l) ASSUME=list ;;
        h) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done
shift $((OPTIND - 1))

if [[ $# -ne 1 ]]; then usage >&2; exit 2; fi
DIR=${1%/}
[[ -d $DIR ]] || { echo "error: no such directory: $DIR" >&2; exit 2; }

# ---------------------------------------------------------------- collect ---
mapfile -t FILES < <(grep -ls "$PATTERN" "$DIR"/RUN_CEEX_*/* 2>/dev/null | sort)
if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "error: no files containing '$PATTERN' under $DIR/RUN_CEEX_*/" >&2
    exit 1
fi

TABLE=$(mktemp); trap 'rm -f "$TABLE"' EXIT

# one awk pass: parse the last "Total" line of every file, then flag outliers
printf '%s\n' "${FILES[@]}" | awk -v errfac="$ERRFAC" -v nmad="$NMAD" '
function median(a, n,   i, b) {
    for (i = 1; i <= n; i++) b[i] = a[i]
    asort(b)
    return (n % 2) ? b[(n+1)/2] : (b[n/2] + b[n/2+1]) / 2
}
{
    f = $0
    while ((getline line < f) > 0) {
        if (line !~ /Total cross-section/) continue
        sub(/.*:[[:space:]]*/, "", line)     # keep "  3.23  +/-  1.3E-003"
        gsub(/[dD]/, "e", line)              # Fortran D exponents
        sub(/\+\/-/, " ", line)
        split(line, b, /[[:space:]]+/)
        if (b[1] == "") { for (i = 1; i <= 3; i++) if (b[i] != "") { b[1] = b[i]; b[2] = b[i+1]; break } }
        v[f] = b[1] + 0; e[f] = b[2] + 0
    }
    close(f)
    if (f in v) { n++; name[n] = f; vals[n] = v[f]; errs[n] = e[f] }
}
END {
    if (n == 0) exit 1
    mv = median(vals, n); me = median(errs, n)
    for (i = 1; i <= n; i++) d[i] = (vals[i] > mv) ? vals[i] - mv : mv - vals[i]
    mad = median(d, n) * 1.4826
    if (mad <= 0) mad = (me > 0) ? me : 1e-30
    printf "#median\t%.10g\t%.3g\t%.3g\n", mv, me, mad
    for (i = 1; i <= n; i++) {
        pull = d[i] / mad
        rat  = (me > 0) ? errs[i] / me : 0
        why = ""
        if (rat  > errfac) why = why sprintf("error x%.0f  ", rat)
        if (pull > nmad)   why = why sprintf("value %.1f sigma  ", pull)
        printf "%s\t%.10g\t%.3g\t%.1f\t%.1f\t%s\n", \
               name[i], vals[i], errs[i], rat, pull, (why == "" ? "-" : why)
    }
}' > "$TABLE" || { echo "error: could not parse any cross-section" >&2; exit 1; }

read -r _ MEDV MEDE MADV < <(grep '^#median' "$TABLE" | tr '\t' ' ')
NTOT=$(grep -vc '^#median' "$TABLE")
mapfile -t BAD < <(grep -v '^#median' "$TABLE" | awk -F'\t' '$6 != "-"')

printf '%d runs in %s\n' "$NTOT" "$DIR"
printf 'median sigma = %s nb   median error = %s   robust spread = %s\n\n' \
       "$MEDV" "$MEDE" "$MADV"

if [[ ${#BAD[@]} -eq 0 ]]; then
    echo "no diverged runs (error < ${ERRFAC}x median, value within ${NMAD} sigma)"
    exit 0
fi

printf '%-46s %14s %12s %7s %8s  %s\n' RUN VALUE ERROR ERR/MED PULL REASON
while IFS=$'\t' read -r f v e r p why; do
    printf '%-46s %14.8g %12.4g %7s %8s  %s\n' \
           "${f#$DIR/}" "$v" "$e" "${r}x" "$p" "$why"
done < <(printf '%s\n' "${BAD[@]}")
printf '\n%d of %d runs flagged\n' "${#BAD[@]}" "$NTOT"

[[ $ASSUME == list ]] && exit 0

# ----------------------------------------------------------------- delete ---
ndel=0
while IFS=$'\t' read -r f v e r p why; do
    if [[ $MODE == dir ]]; then target=$(dirname "$f"); else target=$f; fi
    ans=y
    if [[ $ASSUME == ask ]]; then
        printf '\n  %s = %.8g +/- %.3g  (%s)\n' "${f#$DIR/}" "$v" "$e" "$why"
        printf '  delete %s ? [y]es / [n]o / [a]ll / [q]uit: ' "$target"
        read -r ans < /dev/tty || ans=q
        case ${ans,,} in
            a) ASSUME=yes; ans=y ;;
            q) echo "  stopped."; break ;;
            y) ;;
            *) echo "  kept."; continue ;;
        esac
    fi
    rm -rf -- "$target" && { echo "  removed $target"; ndel=$((ndel + 1)); }
done < <(printf '%s\n' "${BAD[@]}")

printf '\n%d deleted, %d flagged runs left\n' "$ndel" "$(( ${#BAD[@]} - ndel ))"
