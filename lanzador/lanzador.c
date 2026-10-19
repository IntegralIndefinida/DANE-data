/*
 * Lanzador de dane-data para Windows ("Abrir dane-data.exe").
 *
 * Hace lo mismo que "Abrir dane-data (Windows).bat": la primera vez instala "uv" (que a su vez trae
 * Python y las librerías) y luego abre la app con las versiones exactas de uv.lock. Existe porque
 * Windows no permite firmar archivos .bat y un .exe sí. Se compila con lanzador/compilar.sh.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wchar.h>

#define LARGO 32768  /* máximo de una variable de entorno o una ruta larga en Windows */

static wchar_t carpeta[LARGO], ruta[LARGO], comando[LARGO], path[LARGO];

static void escribir(const wchar_t *texto) {
    HANDLE salida = GetStdHandle(STD_OUTPUT_HANDLE);
    DWORD n;
    if (!WriteConsoleW(salida, texto, (DWORD)wcslen(texto), &n, NULL)) {
        /* Salida redirigida (no es una consola): se escribe en UTF-8 */
        char buf[2048];
        int bytes = WideCharToMultiByte(CP_UTF8, 0, texto, -1, buf, sizeof buf, NULL, NULL);
        if (bytes > 1) WriteFile(salida, buf, (DWORD)bytes - 1, &n, NULL);
    }
}

static int pausa_y_salir(int codigo) {
    HANDLE entrada = GetStdHandle(STD_INPUT_HANDLE);
    wchar_t c[256];
    DWORD n;
    escribir(L"\nPresione Enter para cerrar esta ventana...");
    FlushConsoleInputBuffer(entrada);
    if (!ReadConsoleW(entrada, c, 256, &n, NULL)) ReadFile(entrada, c, 1, &n, NULL);
    return codigo;
}

/* Ejecuta la línea de comandos y espera a que termine; devuelve su código de salida, o -1 si no arrancó. */
static long ejecutar(wchar_t *linea) {
    STARTUPINFOW si = {sizeof si};
    PROCESS_INFORMATION pi;
    DWORD codigo = 1;
    if (!CreateProcessW(NULL, linea, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) return -1;
    WaitForSingleObject(pi.hProcess, INFINITE);
    GetExitCodeProcess(pi.hProcess, &codigo);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return (long)codigo;
}

static int buscar_uv(void) {
    return SearchPathW(NULL, L"uv.exe", NULL, LARGO, ruta, NULL) > 0;
}

/* Ctrl+C lo atiende la app (cierra Streamlit); el lanzador solo espera a que termine. Un manejador, y no
   SetConsoleCtrlHandler(NULL, TRUE), porque esa forma la heredan los procesos hijos. */
static BOOL WINAPI ignorar_ctrl_c(DWORD evento) {
    return evento == CTRL_C_EVENT || evento == CTRL_BREAK_EVENT;
}

int wmain(void) {
    wchar_t *barra;
    DWORD largo;

    SetConsoleTitleW(L"dane-data");
    SetConsoleCtrlHandler(ignorar_ctrl_c, TRUE);

    /* Trabaja en la carpeta del .exe, donde están pyproject.toml y uv.lock */
    largo = GetModuleFileNameW(NULL, carpeta, LARGO);
    if (largo == 0 || largo >= LARGO || !(barra = wcsrchr(carpeta, L'\\'))) return 1;
    *barra = L'\0';
    SetCurrentDirectoryW(carpeta);

    /* uv se instala en %USERPROFILE%\.local\bin */
    largo = GetEnvironmentVariableW(L"USERPROFILE", ruta, MAX_PATH);
    if (largo > 0 && largo < MAX_PATH) {
        largo = GetEnvironmentVariableW(L"PATH", comando, LARGO);
        if (largo < LARGO && swprintf(path, LARGO, L"%ls\\.local\\bin;%ls", ruta, comando) > 0)
            SetEnvironmentVariableW(L"PATH", path);
    }

    escribir(L"==============================================\n"
             L"  dane-data - Microdatos del DANE\n"
             L"==============================================\n");

    if (!buscar_uv()) {
        escribir(L"\nPrimera vez: instalando el asistente uv, unos segundos...\n");
        /* Sin tocar el PATH del usuario: este lanzador agrega esa carpeta solo para sí mismo. */
        SetEnvironmentVariableW(L"UV_NO_MODIFY_PATH", L"1");
        /* Ruta completa de PowerShell, para no ejecutar un powershell.exe que esté en la carpeta del zip */
        GetSystemDirectoryW(ruta, MAX_PATH);
        swprintf(comando, LARGO,
                 L"\"%ls\\WindowsPowerShell\\v1.0\\powershell.exe\" -NoProfile -ExecutionPolicy Bypass "
                 L"-Command \"irm https://astral.sh/uv/install.ps1 | iex\"",
                 ruta);
        ejecutar(comando);
        SetEnvironmentVariableW(L"UV_NO_MODIFY_PATH", NULL);
        if (!buscar_uv()) {
            escribir(L"\nNo se pudo instalar uv. Revise su conexión a internet e intente de nuevo.\n");
            return pausa_y_salir(1);
        }
    }

    escribir(L"\nPreparando la aplicación... la primera vez tarda 1 a 3 minutos: descarga Python y librerías.\n\n");
    swprintf(comando, LARGO, L"\"%ls\" run --frozen --quiet --extra app dane-data app", ruta);
    if (ejecutar(comando) != 0) {
        escribir(L"\nLa aplicación se cerró con un error. Si persiste, envíe una captura de esta ventana.\n");
        return pausa_y_salir(1);
    }
    return 0;
}
