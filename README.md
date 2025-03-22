# code2md

## Convert text files in specified directories to Markdown code blocks

### Features

1. Support recursive traversal and multiple filtering criteria
2. Automatic code language recognition
3. Support .gitignore rules and custom exclusion patterns
4. Provide advanced features like file checksum, interactive mode

### Usage

```text
usage: main.py [-h] [-t TYPE] [-R] [-o OUTPUT] [-d DIRECTORY] [-A] [-e EXCLUDE] [--gitignore] [-D MAX_DEPTH] [--encoding ENCODING] [--dry-run] [-v] [-G CONTENT_GREP]
               [--file-size FILE_SIZE] [--modified-time MODIFIED_TIME] [-l] [--checksum] [--no-color] [-i] [--no-warn]

Directory traversal tool for text files

options:
  -h, --help            show this help message and exit
  -t, --type TYPE       Specify file extensions (repeatable, e.g., -t py -t txt)
  -R, --recursive       Recursively traverse subdirectories
  -o, --output OUTPUT   Output file (default: stdout)
  -d, --directory DIRECTORY
                        Target directory (default: current directory)
  -A, --include-invisible
                        Include hidden files
  -e, --exclude EXCLUDE
                        Exclusion patterns (repeatable, supports wildcards)
  --gitignore           Use .gitignore rules
  -D, --max-depth MAX_DEPTH
                        Maximum recursion depth
  --encoding ENCODING   File encoding (default: auto-detect)
  --dry-run             Show file list only, no output generation
  -v, --version         show program's version number and exit
  -G, --content-grep CONTENT_GREP
                        Content regex filter
  --file-size FILE_SIZE
                        File size filter (e.g., '>1K', '<=500B')
  --modified-time MODIFIED_TIME
                        Modification time filter (e.g., '>2023-01-01')
  -l, --follow-symlinks
                        Follow symbolic links
  --checksum            Show MD5 checksum
  --no-color            Disable colored output
  -i, --interactive     Interactive file processing confirmation
  --no-warn             Suppress dependency warnings
```

### Notice

When using `--exclude` option, use `<dir>/**` or `<dir>/` to recursively exclude all subdirectories and files and use `<dir>/*` to only exclude files in specified directory.
