陳宥翔 高心宇
社群網頁架設

本專案使用 **Docker** 作為虛擬環境管理工具，以確保專案可以在任何電腦上重現。

### 執行 Flask 專案的步驟：

1. **確保電腦已安裝並啟動 Docker Desktop**。
2. **開啟終端機 (Terminal)**，並切換到本專案的根目錄（即包含 Dockerfile 的資料夾）。
3. **建立 Docker 映像檔 (Build Image)**：
   在終端機輸入以下指令建立映像檔（注意最後面有一個點 `.`）：
   ```bash
   docker build -t final_project .
   docker run -d -p 5000:5000 --name web_server final_project


本專案支援影片上傳，為了讓網頁播放時有聲音，需要安裝 FFmpeg。

Windows:
winget install -e --id Gyan.FFmpeg

安裝後確認:
ffmpeg -version
