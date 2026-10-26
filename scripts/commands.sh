# Command reference only. Copy individual examples; never execute/source this file.
# Bash, repository root. Requires Python >=3.8 and pip in an existing isolated environment.
# Manifest exposes machine-info and declares psutil/distro/jsonschema/rich; no lockfile is supplied.
# Install the local package via its declared Hatchling backend.
python -m pip install .

# Display parser help without collecting a report (dependency imports still occur).
machine-info --help

# PRIVACY: reports contain usernames, machine IDs, hostname, MAC/IP addresses, listening ports,
# mount paths and PATH. Inspect/redact before sharing; "safe" metadata is NOT anonymization.
# There are no selection, exclude, redact, remote-host, or dry-run flags.
# Collect compact JSON to stdout.
machine-info

# Pretty JSON to stdout or colorized Rich output; --rich implies pretty.
machine-info --pretty
# Alternative: Rich terminal formatting.
machine-info --rich

# Save to an existing parent directory; output is POSITIONAL, not --output.
# Existing file is overwritten without confirmation. Keep the report private.
machine-info "YOUR_PRIVATE_OUTPUT/report.json" --pretty

# Validate fresh collected data against the repository schema before output.
# This does NOT validate an existing report: positional input is always an output destination.
# Validation errors exit 1; jsonschema's default validate does not enforce format keywords.
machine-info --validate data/info.schema.json --pretty

# Combine schema validation with private file output; --rich with a file is plain indented JSON.
machine-info "YOUR_PRIVATE_OUTPUT/validated-report.json" --validate data/info.schema.json --rich

# Equivalent module entry, useful if the installed console script is not on PATH.
python -m machine_info.cli --pretty --validate data/info.schema.json

# Collection depends on OS permissions; unavailable data may silently become empty/default values.
# Do not elevate privileges merely to fill fields. Listening-port enumeration can be incomplete.
# Firewall/VPN/SSH/security booleans, UID/GID and several inventory fields are placeholders,
# NOT verified security findings. macOS/fallback machine IDs are random per collection.
# Metadata collector commit is "unknown"; the report is not evidence of source provenance.
# No tests/lint/deployment/release workflow defined; no machine report was generated during review.
