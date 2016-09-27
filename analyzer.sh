export ECG_FED=FED1
export JYTHONPATH=../ecg_framework_code/build/compling.core.jar:../ecg_framework_code/src/main/nluas/language
jython -m analyzer ../ecg_grammars/winograd.prefs
