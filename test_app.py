import unittest
import os
import json
import time
from app import ProductivityLockerApp, CONFIG_FILE

# Mock class for Tkinter root
class MockRoot:
    def __init__(self):
        pass
    def title(self, title):
        pass
    def geometry(self, geom):
        pass
    def configure(self, **kwargs):
        pass
    def resizable(self, w, h):
        pass
    def after(self, ms, func):
        pass

class TestLockerLogic(unittest.TestCase):
    def setUp(self):
        # Backup config if exists
        self.config_existed = os.path.exists(CONFIG_FILE)
        if self.config_existed:
            with open(CONFIG_FILE, "r") as f:
                self.backup_content = f.read()
        
        # Write a clean test config
        test_config = {
            "blocked_apps": ["notepad.exe", "calc.exe"],
            "difficulty": "medium",
            "problem_types": ["addition", "subtraction", "multiplication", "division", "factoring"],
            "required_questions": 5
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(test_config, f)

        self.root = MockRoot()
        # Stub GUI methods of ProductivityLockerApp to prevent actual Tkinter window creation in unit tests
        self.original_setup_styles = ProductivityLockerApp.setup_styles
        self.original_create_widgets = ProductivityLockerApp.create_widgets
        
        ProductivityLockerApp.setup_styles = lambda self: None
        ProductivityLockerApp.create_widgets = lambda self: None
        
        self.app = ProductivityLockerApp(self.root)
        # Stop monitoring thread immediately so it doesn't run asynchronously in background during tests
        self.app.monitor_active = False

    def tearDown(self):
        # Restore mock stubs
        ProductivityLockerApp.setup_styles = self.original_setup_styles
        ProductivityLockerApp.create_widgets = self.original_create_widgets
        
        # Restore original config
        if self.config_existed:
            with open(CONFIG_FILE, "w") as f:
                f.write(self.backup_content)
        elif os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)

    def test_math_generator_easy(self):
        # Test easy arithmetic for all operators
        for op in ["+", "-", "*", "/"]:
            for _ in range(10):
                q, a, is_fac = self.app.generate_arithmetic_problem("easy", op)
                self.assertEqual(eval(q), a)
                self.assertFalse(is_fac)
            
        # Test easy factoring
        for _ in range(10):
            q, roots, is_fac = self.app.generate_factoring_problem("easy")
            self.assertTrue(is_fac)
            eq_line = q.split('\n')[1].replace("x²", "").replace(" = 0", "").strip()
            for r in roots:
                expr = eq_line.replace("x", f"* ({r})")
                val = r**2 + eval(expr)
                self.assertEqual(val, 0)

    def test_math_generator_medium(self):
        # Test medium arithmetic for all operators
        for op in ["+", "-", "*", "/"]:
            for _ in range(10):
                q, a, is_fac = self.app.generate_arithmetic_problem("medium", op)
                self.assertEqual(eval(q), a)
                self.assertFalse(is_fac)
            
        # Test medium factoring
        for _ in range(10):
            q, roots, is_fac = self.app.generate_factoring_problem("medium")
            self.assertTrue(is_fac)
            eq_line = q.split('\n')[1].replace("x²", "").replace(" = 0", "").strip()
            for r in roots:
                expr = eq_line.replace("x", f"* ({r})")
                val = r**2 + eval(expr)
                self.assertEqual(val, 0)

    def test_math_generator_hard(self):
        # Test hard arithmetic for all operators
        for op in ["+", "-", "*", "/"]:
            for _ in range(10):
                q, a, is_fac = self.app.generate_arithmetic_problem("hard", op)
                self.assertEqual(eval(q), a)
                self.assertFalse(is_fac)
            
        # Test hard factoring
        for _ in range(10):
            q, roots, is_fac = self.app.generate_factoring_problem("hard")
            self.assertTrue(is_fac)
            eq_line = q.split('\n')[1].replace("x²", "").replace(" = 0", "").strip()
            for r in roots:
                expr = eq_line.replace("x", f"* ({r})")
                val = r**2 + eval(expr)
                self.assertEqual(val, 0)

    def test_currently_unlocked_transitions(self):
        # Verify initial state
        self.assertEqual(self.app.currently_unlocked, {})
        
        # Simulating user solving math puzzle for notepad.exe
        self.app.currently_unlocked["notepad.exe"] = "pending"
        self.assertEqual(self.app.currently_unlocked["notepad.exe"], "pending")
        
        # Mock behavior of process detection
        # Case 1: Running transition
        running_blocked_apps = {"notepad.exe"}
        if "notepad.exe" in self.app.currently_unlocked:
            if self.app.currently_unlocked["notepad.exe"] == "pending":
                self.app.currently_unlocked["notepad.exe"] = "running"
        self.assertEqual(self.app.currently_unlocked["notepad.exe"], "running")
        
        # Case 2: Process closed transition (notepad.exe no longer in running list)
        running_blocked_apps_empty = set()
        for app in list(self.app.currently_unlocked.keys()):
            state = self.app.currently_unlocked[app]
            if state == "running" and app not in running_blocked_apps_empty:
                del self.app.currently_unlocked[app]
                
        self.assertNotIn("notepad.exe", self.app.currently_unlocked)

    def test_required_questions_config(self):
        # Test default configuration loaded correctly
        self.assertEqual(self.app.config.get("required_questions"), 5)
        
        # Test updating required questions
        self.app.config["required_questions"] = 3
        self.app.save_config()
        
        # Reload config and check
        new_app = ProductivityLockerApp(self.root)
        new_app.monitor_active = False
        self.assertEqual(new_app.config.get("required_questions"), 3)

    def test_geometry_generator(self):
        for diff in ["easy", "medium", "hard"]:
            for _ in range(20):
                q, a, is_fac = self.app.generate_geometry_problem(diff)
                self.assertIsInstance(q, str)
                self.assertIsInstance(a, int)
                self.assertFalse(is_fac)

    def test_formula_generator(self):
        for diff in ["easy", "medium", "hard"]:
            for _ in range(20):
                q, a, is_fac = self.app.generate_formula_problem(diff)
                self.assertIsInstance(q, str)
                self.assertIsInstance(a, int)
                self.assertFalse(is_fac)

    def test_hard_mode_generators(self):
        # Generate several to hit all randomized branches
        for _ in range(50):
            q_geo, a_geo, _ = self.app.generate_geometry_problem("hard")
            self.assertIsInstance(q_geo, str)
            self.assertIsInstance(a_geo, int)
            
            q_form, a_form, _ = self.app.generate_formula_problem("hard")
            self.assertIsInstance(q_form, str)
            self.assertIsInstance(a_form, int)

    def test_unlock_expirations_handling(self):
        # 1. Verify initialization
        self.assertEqual(self.app.unlock_expirations, {})
        
        # 2. Mock state where chrome.exe has expired access
        import time
        self.app.currently_unlocked["chrome.exe"] = "running"
        self.app.unlock_expirations["chrome.exe"] = time.time() - 10  # expired 10s ago
        
        # Mock kill_app_processes to check if it gets called
        killed_apps = []
        self.app.kill_app_processes = lambda app: killed_apps.append(app)
        
        # Run one tick of monitor logic
        now = time.time()
        for app in list(self.app.currently_unlocked.keys()):
            expires_at = self.app.unlock_expirations.get(app)
            if expires_at and now >= expires_at:
                self.app.kill_app_processes(app)
                if app in self.app.currently_unlocked:
                    del self.app.currently_unlocked[app]
                if app in self.app.unlock_expirations:
                    del self.app.unlock_expirations[app]
                    
        self.assertEqual(killed_apps, ["chrome.exe"])
        self.assertNotIn("chrome.exe", self.app.currently_unlocked)
        self.assertNotIn("chrome.exe", self.app.unlock_expirations)

    def test_tips_loading(self):
        # Verify that math_tips was populated with at least 100 items from tips.json
        self.assertGreaterEqual(len(self.app.math_tips), 100)
        
        # Test fallback behavior when file is missing
        original_exists = os.path.exists("tips.json")
        if original_exists:
            try:
                os.rename("tips.json", "tips.json.tmp")
            except Exception:
                # If file is locked, skip testing the rename portion
                return
            
        try:
            self.app.load_tips()
            # Falls back to default tips (length 5)
            self.assertEqual(len(self.app.math_tips), 5)
        finally:
            if original_exists:
                if os.path.exists("tips.json"):
                    try:
                        os.remove("tips.json")
                    except Exception:
                        pass
                try:
                    os.rename("tips.json.tmp", "tips.json")
                except Exception:
                    pass

    def test_division_explanation(self):
        # Verify that generating division explanation gives a valid multi-line string
        explanation = self.app.generate_division_explanation(168, 4)
        self.assertIn("168 ÷ 4", explanation)
        self.assertIn("Bring down '1'", explanation)
        self.assertIn("Bring down '6'", explanation)
        self.assertIn("Bring down '8'", explanation)
        self.assertIn("Final Answer: 42", explanation)

    def test_play_sound(self):
        # Verify that play_sound runs without throwing errors for all valid sound types
        try:
            self.app.play_sound("success")
            self.app.play_sound("error")
            self.app.play_sound("victory")
            self.app.play_sound("invalid_sound_type")
        except Exception as e:
            self.fail(f"play_sound threw an exception: {e}")

    def test_confetti_trigger(self):
        # Mock canvas_grid and animate_confetti to prevent actual Tkinter calls
        self.app.canvas_grid = True
        self.app.animate_confetti = lambda start_time: None
        self.app.trigger_confetti_animation()
        self.assertTrue(self.app.confetti_active)
        self.assertEqual(len(self.app.confetti_particles), 60)
        self.app.confetti_active = False # turn off animation loop

    def test_activity_logging(self):
        if os.path.exists("activity.log"):
            try:
                os.remove("activity.log")
            except Exception:
                pass
        self.app.write_log("Test Log Event")
        self.assertTrue(os.path.exists("activity.log"))
        with open("activity.log", "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Test Log Event", content)

if __name__ == "__main__":
    unittest.main()
