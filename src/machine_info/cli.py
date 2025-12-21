import argparse
import json
import sys
import os
from .collector import collect_all

def main():
    parser = argparse.ArgumentParser(description="Collect machine introspection report.")
    parser.add_argument("output", nargs="?", help="Output file path (default: stdout)", default=None)
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output")
    parser.add_argument("--validate", help="Path to schema file for validation", default=None)
    
    args = parser.parse_args()
    
    try:
        data = collect_all()
        
        if args.validate:
            try:
                from jsonschema import validate, ValidationError
                with open(args.validate, 'r') as f:
                    schema = json.load(f)
                validate(instance=data, schema=schema)
                # print("Validation successful!", file=sys.stderr)
            except ImportError:
                print("jsonschema not installed, skipping validation.", file=sys.stderr)
            except Exception as e:
                print(f"Validation failed: {e}", file=sys.stderr)
                sys.exit(1)

        output_str = json.dumps(data, indent=2 if args.pretty else None, default=str)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output_str)
        else:
            print(output_str)
            
    except Exception as e:
        print(f"Error collecting data: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
