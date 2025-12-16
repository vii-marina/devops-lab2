DevOps Lab 2 – Bash Scripting and Monitoring

This project is part of the DevOps course laboratory work.

Part 1: Bash Scripting

1. Automatic Backup Script (backup.sh)

The backup.sh script performs automatic backups of a specified directory.

Features:
- Creates compressed tar.gz archives
- Adds timestamp to backup file names
- Writes detailed logs of all operations
- Keeps only the last 5 backups and removes older ones
- Handles basic errors (invalid paths, command failures)

Usage example:
./backup.sh /path/to/source_directory /path/to/backup_directory

2. System Monitoring Script (monitoring.sh)

The monitoring.sh script checks system disk usage and sends alerts to Discord when a defined threshold is exceeded.

Features:
- Checks disk usage using df
- Configurable threshold value
- Logs monitoring results to a log file
- Sends alerts to a Discord channel using a webhook
- Graceful handling of missing tools or configuration

Usage example:
./monitoring.sh

Requirements:
- Bash (macOS default bash 3.2+)
- tar
- curl
- Discord webhook URL configured inside monitoring.sh

Notes:
The same Discord channel can be used for multiple DevOps alerts by configuring multiple webhooks.
Part 3: Go CLI tool (File Organizer)

Location:
go/file_organizer/

Build:
cd go/file_organizer
go build -o file-organizer

Usage examples:
./file-organizer -src ~/devops_test_go/input -dest ~/devops_test_go/output -mode copy -recursive -verbose
./file-organizer -src ~/devops_test_go/input -dest ~/devops_test_go/output_move -mode move -recursive -verbose
./file-organizer -src ~/devops_test_go/input -dest ~/devops_test_go/output -mode move -dry-run -verbose

Flags:
-src        source directory to organize (required)
-dest       destination root directory (default: same as src)
-mode       move or copy
-recursive  scan folders recursively
-dry-run    show actions without changing files
-verbose    print detailed actions


