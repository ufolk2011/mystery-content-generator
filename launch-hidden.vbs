Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
proj = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = proj
sh.Environment("Process")("STREAMLIT_BROWSER_GATHER_USAGE_STATS") = "false"
python = proj & "\.venv\Scripts\python.exe"
cmd = """" & python & """ -m streamlit run app.py --server.headless false --browser.gatherUsageStats false"
sh.Run cmd, 0, False
