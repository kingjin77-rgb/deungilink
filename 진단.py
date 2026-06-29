import sys, os, traceback
from pathlib import Path

os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

log_path = Path(__file__).parent / "오류내용.txt"

try:
    import main
    main.main()
except Exception as e:
    err = traceback.format_exc()
    log_path.write_text(err, encoding='utf-8')
    print("오류 발생! 오류내용.txt 파일을 확인하세요.")
    print(err)
    input("엔터를 누르면 종료...")
except SystemExit:
    pass
