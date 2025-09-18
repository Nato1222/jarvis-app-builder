"""
Executor Worker

This worker picks up approved missions and executes their steps
using the ToolBelt service.
"""
import time
import sqlite3
from ..database.database import get_connection
from ..services.toolbelt import tool_belt

def run_executor_worker():
    """
    A simple loop to pick up and execute missions.
    """
    print("[ExecutorWorker]: Starting worker loop...")
    while True:
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Find an approved mission that hasn't been started
            cursor.execute("SELECT * FROM missions WHERE status = 'approved' LIMIT 1")
            mission = cursor.fetchone()

            if mission:
                print(f"[ExecutorWorker]: Picked up mission {mission['mission_id']}")
                mission_id = mission['mission_id']
                
                try:
                    # Update status to 'in_progress'
                    cursor.execute("UPDATE missions SET status = 'in_progress' WHERE mission_id = ?", (mission_id,))
                    conn.commit()

                    steps = mission['steps'] # Assuming steps are stored as JSON string
                    import json
                    steps_data = json.loads(steps)

                    for step in steps_data:
                        print(f"  Executing step: {step['description']}")
                        tool_belt.execute_tool(step['tool'], step['action'], step['params'])
                    
                    # If all steps succeed, mark as completed
                    cursor.execute("UPDATE missions SET status = 'completed' WHERE mission_id = ?", (mission_id,))
                    conn.commit()
                    print(f"[ExecutorWorker]: Mission {mission_id} completed successfully.")

                except Exception as e:
                    print(f"[ExecutorWorker]: Mission {mission_id} failed. Status set to 'blocked'. Error: {e}")
                    cursor.execute("UPDATE missions SET status = 'blocked' WHERE mission_id = ?", (mission_id,))
                    conn.commit()

            else:
                # No missions to run, wait for a bit
                time.sleep(10)

        except sqlite3.Error as e:
            print(f"[ExecutorWorker]: Database error: {e}")
            time.sleep(15)
        except Exception as e:
            print(f"[ExecutorWorker]: An unexpected error occurred: {e}")
            time.sleep(15)
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
    run_executor_worker()
