import os
import zipfile
import datetime

def backup_project(source_dir, output_zip):
    # Folders to exclude completely
    exclude_dirs = {'.venv', '.git', '__pycache__', 'browser_data', 'dist', 'synthflow_offline_pkg', '.idea', '.vscode'}
    # Files to exclude
    exclude_extensions = {'.pyc', '.zip', '.tar', '.gz', '.log'}

    print(f"Creating backup at: {output_zip}")
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if any(file.endswith(ext) for ext in exclude_extensions):
                    continue
                
                # Avoid backing up the backup script itself if it's running inside? 
                # Or self-referential zips if destination is in source.
                if file == os.path.basename(output_zip):
                    continue

                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                
                try:
                    zipf.write(file_path, arcname)
                except Exception as e:
                    print(f"Skipped {file}: {e}")

if __name__ == "__main__":
    # Assumes script is in E:\projects\SynthFlow\scripts
    # We want to backup E:\projects\SynthFlow
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir) # Go up one level
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    output_filename = f"SynthFlow_Source_v0.5_{timestamp}.zip"
    output_path = os.path.join(project_root, output_filename)
    
    print(f"Backing up project root: {project_root}")
    backup_project(project_root, output_path)
    print(f"Backup successfully created: {output_path}")
