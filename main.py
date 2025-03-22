#!/bin/env python
# -*- coding: utf-8 -*-
"""
code2md - Convert text files in specified directories to Markdown code blocks
Version: 0.0.1
Features:
1. Support recursive traversal and multiple filtering criteria
2. Automatic code language recognition
3. Support .gitignore rules and custom exclusion patterns
4. Provide advanced features like file checksum, interactive mode
"""

import os
import sys
import argparse
import re
import hashlib
from datetime import datetime
from fnmatch import fnmatch
from pypinyin import lazy_pinyin  # For Chinese filename sorting
import locale
import mimetypes  # Fallback MIME type detection

# Try importing magic library for accurate file type detection
try:
    from magic import Magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

__version__ = "0.0.1"  # Tool version

# File extension to Markdown language mapping
LANGUAGE_MAP = {
    'py': 'python',
    'js': 'javascript',
    'java': 'java',
    'c': 'c',
    'cpp': 'cpp',
    'html': 'html',
    'css': 'css',
    'php': 'php',
    'json': 'json',
    'xml': 'xml',
    'sql': 'sql',
    'sh': 'bash',
    'md': 'markdown'
}

def parse_gitignore(gitignore_path):
    """
    Parse .gitignore file and return exclusion patterns
    
    Args:
        gitignore_path (str): Path to .gitignore file
        
    Returns:
        list: List of exclusion patterns
    """
    patterns = []
    try:
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
    except FileNotFoundError:
        pass
    return patterns

def should_exclude(path, patterns, root_dir):
    """
    Determine if a file/directory should be excluded
    
    Args:
        path (str): Full path to check
        patterns (list): List of exclusion patterns
        root_dir (str): Root directory path
        
    Returns:
        bool: True if should be excluded, False otherwise
    """
    rel_path = os.path.relpath(path, root_dir).replace(os.sep, '/')
    is_dir = os.path.isdir(path)
    
    for pattern in patterns:
        # Normalize pattern format
        p = pattern.lstrip('/')  # Remove leading slash
        p = p.replace(os.sep, '/').rstrip('/')
        
        # Handle absolute path matching
        if pattern.startswith('/'):
            if rel_path == p:
                return True
        
        # Handle directory recursive exclusion
        if pattern.endswith('/'):
            p += '/**'  # Convert to recursive matching
        
        # Convert wildcard syntax
        if p.endswith('*') and not p.endswith('**'):
            p = p.rstrip('*') + '/*'  # Match direct children
        
        # Build complete match pattern
        if '/' in p:
            match_pattern = p
        else:
            match_pattern = '**/' + p
        
        # Perform pattern matching with fnmatch
        if fnmatch(rel_path, match_pattern):
            return True
        if is_dir and fnmatch(rel_path + '/', match_pattern + '/*'):
            return True
            
    return False

def get_sort_key(path, root_dir):
    """
    Generate sorting key for files to achieve:
    1. Sort by directory depth (shallow first)
    2. Sort by pinyin for same level directories
    
    Args:
        path (str): Full file path
        root_dir (str): Root directory path
        
    Returns:
        tuple: Sorting key
    """
    rel_path = os.path.relpath(path, root_dir)
    parts = rel_path.split(os.sep)
    depth = len(parts) - 1
    
    def trans(name):
        """Convert Chinese characters to pinyin"""
        try:
            return ''.join(lazy_pinyin(name))
        except:
            return name.lower()
    
    return (
        -depth,  # Negative for shallow-first sorting
        *[trans(p) for p in parts[:-1]],  # Parent directories in pinyin
        trans(parts[-1])  # Current filename in pinyin
    )

def is_text_file(filepath):
    """
    Determine if a file is text-based
    
    Args:
        filepath (str): File path
        
    Returns:
        bool: True if text file, False otherwise
    """
    # Choose detection method based on available libraries
    if HAS_MAGIC:
        mime = Magic(mime=True).from_file(filepath)
    else:
        mime_type, _ = mimetypes.guess_type(filepath)
        mime = mime_type or 'application/octet-stream'
    
    # MIME type judgment
    if mime.startswith('text/'):
        return True
    # Additional text type checks
    if mime in {'application/json', 'application/xml'}:
        return True
    return False

def get_file_language(filename):
    """
    Get Markdown code language based on filename
    
    Args:
        filename (str): Filename
        
    Returns:
        str: Markdown code language identifier
    """
    ext = filename.split('.')[-1].lower()
    return LANGUAGE_MAP.get(ext, 'text')

def parse_operator_value(pattern):
    """
    Parse operator-value combination string (e.g., ">1K")
    
    Args:
        pattern (str): Operator-value string
        
    Returns:
        tuple: (operator, value)
        
    Raises:
        ValueError: If invalid format
    """
    match = re.match(r'([<>=]+)(.+)', pattern)
    if not match:
        raise ValueError(f"Invalid pattern: {pattern}")
    op = match.group(1)
    value = match.group(2)
    return op, value

def process_directory(args):
    """
    Process directory traversal and file filtering
    
    Args:
        args (Namespace): Command line arguments object
        
    Returns:
        list: List of qualified file paths
    """
    text_files = []
    root_dir = os.path.abspath(args.directory)
    exclude_patterns = args.exclude if args.exclude else []
    gitignore_patterns = parse_gitignore(os.path.join(root_dir, '.gitignore')) if args.gitignore else []
    all_exclude_patterns = exclude_patterns + gitignore_patterns
    
    # Walk directory tree
    for dirpath, dirnames, filenames in os.walk(root_dir, followlinks=args.follow_symlinks):
        # Depth control
        current_depth = dirpath[len(root_dir):].count(os.sep)
        if args.max_depth is not None and current_depth >= args.max_depth:
            del dirnames[:]
            continue
        
        # Hidden files handling
        if not args.include_invisible:
            dirnames[:] = [d for d in dirnames if not d.startswith('.')]
            filenames = [f for f in filenames if not f.startswith('.')]
        
        # Symbolic links handling
        if not args.follow_symlinks:
            dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]
            filenames = [f for f in filenames if not os.path.islink(os.path.join(dirpath, f))]
        
        # File filtering
        for f in filenames:
            full_path = os.path.join(dirpath, f)
            
            # Exclusion check
            if should_exclude(full_path, all_exclude_patterns, root_dir):
                continue
            
            # File type filter
            if args.type:
                ext = os.path.splitext(f)[1].lower()
                if not ext or ext[1:] not in {t.lower().lstrip('.') for t in args.type}:
                    continue
            
            # File size filter
            if args.file_size:
                file_size = os.path.getsize(full_path)
                try:
                    op, size = parse_operator_value(args.file_size)
                    size = size.upper()
                    multiplier = 1
                    if size[-1] in 'KMGTP':
                        multiplier = 1024 ** ('BKMGTP'.index(size[-1]))
                        size = size[:-1]
                    target_size = int(size) * multiplier
                except (ValueError, IndexError):
                    continue
                
                # Perform size comparison
                if op == '>=' and not (file_size >= target_size):
                    continue
                elif op == '<=' and not (file_size <= target_size):
                    continue
                elif op == '>' and not (file_size > target_size):
                    continue
                elif op == '<' and not (file_size < target_size):
                    continue
                elif op == '==' and not (file_size == target_size):
                    continue
            
            # Modification time filter
            if args.modified_time:
                mtime = os.path.getmtime(full_path)
                file_time = datetime.fromtimestamp(mtime)
                try:
                    op, date_str = parse_operator_value(args.modified_time)
                    target_time = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    continue
                
                # Perform time comparison
                if op == '>' and not (file_time > target_time):
                    continue
                elif op == '<' and not (file_time < target_time):
                    continue
                elif op == '>=' and not (file_time >= target_time):
                    continue
                elif op == '<=' and not (file_time <= target_time):
                    continue
                elif op == '==' and not (file_time.date() == target_time.date()):
                    continue
            
            # Content regex filter
            if args.content_grep and is_text_file(full_path):
                try:
                    with open(full_path, 'r', encoding=args.encoding or 'utf-8') as fh:
                        # Stream reading for large files
                        for line in fh:
                            if re.search(args.content_grep, line):
                                break
                        else:
                            continue
                except:
                    continue
            
            # Final text file confirmation
            if is_text_file(full_path):
                text_files.append(full_path)
    
    # Non-recursive mode filtering
    if not args.recursive:
        text_files = [f for f in text_files if os.path.dirname(f) == root_dir]
    
    # Sorting
    text_files.sort(key=lambda x: get_sort_key(x, root_dir))
    return text_files

def write_markdown(args, files):
    """
    Write file list to Markdown format output
    
    Args:
        args (Namespace): Command line arguments object
        files (list): List of file paths
    """
    root_dir = os.path.abspath(args.directory)
    output = sys.stdout if args.output == '-' else open(args.output, 'w', encoding='utf-8')
    
    try:
        # Dependency warning
        if not HAS_MAGIC and not args.no_warn:
            print("Warning: python-magic not installed, using basic MIME detection", file=sys.stderr)
        
        # Process files
        for idx, f in enumerate(files, 1):
            rel_path = os.path.relpath(f, root_dir)
            
            # Interactive confirmation
            if args.interactive:
                choice = None
                while choice not in ('', 'y', 'n'):
                    choice = input(f"Process file {rel_path}? [Y/n] ").strip().lower()
                if choice == 'n':
                    continue
            
            # Calculate checksum
            checksum = ''
            if args.checksum:
                with open(f, 'rb') as fh:
                    checksum = hashlib.md5(fh.read()).hexdigest()
            
            # Build Markdown header
            header = f"# {rel_path}"
            if checksum:
                header += f" (MD5: {checksum})"
            
            # Auto-detect code language
            language = get_file_language(os.path.basename(f))
            output.write(f"{header}\n\n```{language}\n")
            
            # Read and write file content
            try:
                with open(f, 'r', encoding=args.encoding or 'utf-8') as fh:
                    for line in fh:
                        output.write(line)
            except UnicodeDecodeError:
                # Try GBK encoding
                try:
                    with open(f, 'r', encoding='gbk') as fh:
                        output.write(fh.read())
                except:
                    output.write("<<Unable to decode file content>>\n")
            except Exception as e:
                output.write(f"<<File read error: {str(e)}>>\n")
            
            output.write("\n```\n\n")
            
            # Console progress output
            if args.no_color:
                print(f"Processed file: {rel_path}")
            else:
                print(f"\033[32mProcessed:\033[0m {rel_path}")
    finally:
        if output != sys.stdout:
            output.close()

def main():
    """Main function: Parse arguments and execute program"""
    parser = argparse.ArgumentParser(description="Directory traversal tool for text files")
    # Argument definitions
    parser.add_argument('-t', '--type', action='append',
                      help="Specify file extensions (repeatable, e.g., -t py -t txt)")
    parser.add_argument('-R', '--recursive', action='store_true',
                      help="Recursively traverse subdirectories")
    parser.add_argument('-o', '--output', default='-',
                      help="Output file (default: stdout)")
    parser.add_argument('-d', '--directory', default=os.getcwd(),
                      help="Target directory (default: current directory)")
    parser.add_argument('-A', '--include-invisible', action='store_true',
                      help="Include hidden files")
    parser.add_argument('-e', '--exclude', action='append',
                      help="Exclusion patterns (repeatable, supports wildcards)")
    parser.add_argument('--gitignore', action='store_true',
                      help="Use .gitignore rules")
    parser.add_argument('-D', '--max-depth', type=int,
                      help="Maximum recursion depth")
    parser.add_argument('--encoding',
                      help="File encoding (default: auto-detect)")
    parser.add_argument('--dry-run', action='store_true',
                      help="Show file list only, no output generation")
    parser.add_argument('-v', '--version', action='version',
                      version=f'%(prog)s {__version__}')
    parser.add_argument('-G', '--content-grep',
                      help="Content regex filter")
    parser.add_argument('--file-size',
                      help="File size filter (e.g., '>1K', '<=500B')")
    parser.add_argument('--modified-time',
                      help="Modification time filter (e.g., '>2023-01-01')")
    parser.add_argument('-l', '--follow-symlinks', action='store_true',
                      help="Follow symbolic links")
    parser.add_argument('--checksum', action='store_true',
                      help="Show MD5 checksum")
    parser.add_argument('--no-color', action='store_true',
                      help="Disable colored output")
    parser.add_argument('-i', '--interactive', action='store_true',
                      help="Interactive file processing confirmation")
    parser.add_argument('--no-warn', action='store_true',
                      help="Suppress dependency warnings")
    
    args = parser.parse_args()
    
    # Initialize MIME type detection
    if not HAS_MAGIC:
        mimetypes.init()
    
    # Set locale
    try:
        locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
    except locale.Error:
        pass
    
    # Process directory and get file list
    files = process_directory(args)
    
    # Dry-run mode handling
    if args.dry_run:
        for f in files:
            print(os.path.relpath(f, args.directory))
        return
    
    # Generate Markdown output
    write_markdown(args, files)

if __name__ == "__main__":
    main()