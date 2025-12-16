package main

import (
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type Options struct {
	Src       string
	Dest      string
	Mode      string // "move" or "copy"
	Recursive bool
	DryRun    bool
	Verbose   bool
}

func main() {
	opts, err := parseFlags()
	if err != nil {
		fmt.Fprintln(os.Stderr, "ERROR:", err)
		os.Exit(1)
	}

	if err := run(opts); err != nil {
		fmt.Fprintln(os.Stderr, "ERROR:", err)
		os.Exit(1)
	}
}

func parseFlags() (Options, error) {
	var o Options

	flag.StringVar(&o.Src, "src", "", "Source directory to organize")
	flag.StringVar(&o.Dest, "dest", "", "Destination root directory (default: same as src)")
	flag.StringVar(&o.Mode, "mode", "move", "Operation mode: move or copy")
	flag.BoolVar(&o.Recursive, "recursive", false, "Scan directories recursively")
	flag.BoolVar(&o.DryRun, "dry-run", false, "Show what would happen without changing files")
	flag.BoolVar(&o.Verbose, "verbose", false, "Print detailed actions")

	flag.Parse()

	if o.Src == "" {
		return o, errors.New("missing required flag: -src")
	}

	srcAbs, err := filepath.Abs(o.Src)
	if err != nil {
		return o, err
	}
	o.Src = srcAbs

	if o.Dest == "" {
		o.Dest = o.Src
	} else {
		destAbs, err := filepath.Abs(o.Dest)
		if err != nil {
			return o, err
		}
		o.Dest = destAbs
	}

	o.Mode = strings.ToLower(strings.TrimSpace(o.Mode))
	if o.Mode != "move" && o.Mode != "copy" {
		return o, errors.New("invalid -mode (use 'move' or 'copy')")
	}

	info, err := os.Stat(o.Src)
	if err != nil {
		return o, err
	}
	if !info.IsDir() {
		return o, errors.New("-src must be a directory")
	}

	if err := os.MkdirAll(o.Dest, 0755); err != nil {
		return o, err
	}

	return o, nil
}

func run(o Options) error {
	start := time.Now()

	files, err := collectFiles(o.Src, o.Recursive)
	if err != nil {
		return err
	}

	if o.Verbose {
		fmt.Println("Files found:", len(files))
	}

	moved := 0
	skipped := 0
	failed := 0

	for _, srcPath := range files {
		rel, err := filepath.Rel(o.Src, srcPath)
		if err != nil {
			failed++
			fmt.Fprintln(os.Stderr, "WARN: cannot build relative path for", srcPath, ":", err)
			continue
		}

		ext := strings.ToLower(filepath.Ext(srcPath))
		category := categoryByExt(ext)

		destDir := filepath.Join(o.Dest, category)
		destPath := filepath.Join(destDir, filepath.Base(rel))

		if sameFile(srcPath, destPath) {
			skipped++
			continue
		}

		if err := ensureDir(destDir, o.DryRun, o.Verbose); err != nil {
			failed++
			fmt.Fprintln(os.Stderr, "WARN:", err)
			continue
		}

		if o.Verbose || o.DryRun {
			fmt.Printf("%s: %s -> %s\n", strings.ToUpper(o.Mode), srcPath, destPath)
		}

		if o.DryRun {
			moved++
			continue
		}

		if o.Mode == "move" {
			if err := moveFile(srcPath, destPath); err != nil {
				failed++
				fmt.Fprintln(os.Stderr, "WARN: move failed:", err)
				continue
			}
		} else {
			if err := copyFile(srcPath, destPath); err != nil {
				failed++
				fmt.Fprintln(os.Stderr, "WARN: copy failed:", err)
				continue
			}
		}
		moved++
	}

	fmt.Println("Done.")
	fmt.Println("Processed:", len(files))
	fmt.Println("Succeeded:", moved)
	fmt.Println("Skipped:", skipped)
	fmt.Println("Failed:", failed)
	fmt.Println("Duration:", time.Since(start).Round(time.Millisecond))

	return nil
}

func collectFiles(root string, recursive bool) ([]string, error) {
	var out []string

	if !recursive {
		entries, err := os.ReadDir(root)
		if err != nil {
			return nil, err
		}
		for _, e := range entries {
			if e.IsDir() {
				continue
			}
			out = append(out, filepath.Join(root, e.Name()))
		}
		return out, nil
	}

	err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		out = append(out, path)
		return nil
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

func categoryByExt(ext string) string {
	switch ext {
	case ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".tiff":
		return "images"
	case ".mp4", ".mov", ".mkv", ".avi", ".webm":
		return "videos"
	case ".mp3", ".wav", ".flac", ".aac", ".m4a":
		return "audio"
	case ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md":
		return "documents"
	case ".zip", ".tar", ".gz", ".tgz", ".rar", ".7z":
		return "archives"
	case ".go", ".py", ".js", ".ts", ".java", ".c", ".cpp", ".cs", ".html", ".css", ".json", ".yaml", ".yml", ".sh":
		return "code"
	default:
		if ext == "" {
			return "no_extension"
		}
		return "other"
	}
}

func ensureDir(dir string, dryRun bool, verbose bool) error {
	if dryRun {
		if verbose {
			fmt.Println("DRY-RUN: ensure dir", dir)
		}
		return nil
	}
	return os.MkdirAll(dir, 0755)
}

func moveFile(src, dest string) error {
	if err := os.Rename(src, dest); err == nil {
		return nil
	}

	if err := copyFile(src, dest); err != nil {
		return err
	}
	return os.Remove(src)
}

func copyFile(src, dest string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dest)
	if err != nil {
		return err
	}
	defer func() {
		_ = out.Close()
	}()

	if _, err := io.Copy(out, in); err != nil {
		return err
	}
	return out.Sync()
}

func sameFile(a, b string) bool {
	aa, err1 := filepath.Abs(a)
	bb, err2 := filepath.Abs(b)
	if err1 != nil || err2 != nil {
		return false
	}
	return aa == bb
}

