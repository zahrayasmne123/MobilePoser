import subprocess
from pathlib import Path
def run_visualization_process(pred_path):
    """
    Runs the visualization in a separate process.
    Returns True if successful, False otherwise.
    """
    # Create the visualization script content
    script_content = f'''
import sys
from pathlib import Path
from mobileposer.own_device_visualiser import visualize_predictions

if __name__ == "__main__":
    pred_path = Path("{pred_path}")
    try:
        visualize_predictions(pred_path)
        print("Visualization completed successfully")
        sys.exit(0)
    except Exception as e:
        print(f"Error in visualization: {{str(e)}}")
        sys.exit(1)
'''
    
    # Create temporary script
    temp_script = Path("temp_visualize.py")
    temp_script.write_text(script_content)
    
    try:
        # Run the script in a separate process
        result = subprocess.run(
            ["python", str(temp_script)], 
            capture_output=True,
            text=True
        )
        
        # Check if process was successful
        if result.returncode == 0:
            return True, "Visualization completed successfully"
        else:
            return False, f"Visualization failed with output: {result.stderr}"
            
    except Exception as e:
        return False, f"Process error: {str(e)}"
    finally:
        # Cleanup temporary script
        if temp_script.exists():
            temp_script.unlink()


