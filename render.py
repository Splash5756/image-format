import glfw
from OpenGL.GL import *
import numpy as np

# Örnek: rastgele RGBA pixel verisi oluşturuyorum (kendi verinle değiştir)
# Eğer verin farklı ise, uygun şekilde düzenle

def main(width,height, rawpixels):
    # GLFW başlat
    pixels = np.array(rawpixels, dtype=np.uint8)
    pixels = pixels.reshape((height, width, 4))
    pixels = np.flipud(pixels)
    if not glfw.init():
        return

    # Pencere oluştur (OpenGL 3.3 core)
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    # MacOS kullanıyorsan, uncomment:
    # glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_TRUE)

    window = glfw.create_window(width, height, "Custom Image Viewer", None, None)
    if not window:
        glfw.terminate()
        return

    glfw.make_context_current(window)

    # Viewport ayarla
    glViewport(0, 0, width, height)

    # --- Texture oluştur ---
    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)

    # Texture parametreleri (özellikle tekrar modları ve filtreleme)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

    # Texture verisini yükle
    # pixels numpy arrayinin tipinin uint8 ve shape (height, width, 4) RGBA olduğuna dikkat et
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, pixels)

    glBindTexture(GL_TEXTURE_2D, 0)

    # --- Basit vertex ve fragment shader kaynakları ---
    vertex_shader_source = """
    #version 330 core
    layout (location = 0) in vec2 position;
    layout (location = 1) in vec2 texCoords;
    out vec2 TexCoords;
    void main()
    {
        gl_Position = vec4(position.xy, 0.0, 1.0);
        TexCoords = texCoords;
    }
    """

    fragment_shader_source = """
    #version 330 core
    in vec2 TexCoords;
    out vec4 FragColor;
    uniform sampler2D screenTexture;
    void main()
    {
        FragColor = texture(screenTexture, TexCoords);
    }
    """

    # Shader derleme fonksiyonu
    def compile_shader(source, shader_type):
        shader = glCreateShader(shader_type)
        glShaderSource(shader, source)
        glCompileShader(shader)
        # Derleme kontrolü
        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            info_log = glGetShaderInfoLog(shader).decode()
            raise RuntimeError(f"Shader compile error: {info_log}")
        return shader

    # Shader program oluştur
    vertex_shader = compile_shader(vertex_shader_source, GL_VERTEX_SHADER)
    fragment_shader = compile_shader(fragment_shader_source, GL_FRAGMENT_SHADER)
    shader_program = glCreateProgram()
    glAttachShader(shader_program, vertex_shader)
    glAttachShader(shader_program, fragment_shader)
    glLinkProgram(shader_program)
    # Link kontrolü
    if not glGetProgramiv(shader_program, GL_LINK_STATUS):
        info_log = glGetProgramInfoLog(shader_program).decode()
        raise RuntimeError(f"Shader link error: {info_log}")

    # Shaderları silebiliriz (artık bağlı)
    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)

    # --- Quad için vertex verileri (2D full-screen quad) ---
    vertices = np.array([
        # position   # texCoords
        -1.0,  1.0,  0.0, 1.0,  # sol üst
        -1.0, -1.0,  0.0, 0.0,  # sol alt
         1.0, -1.0,  1.0, 0.0,  # sağ alt
         1.0,  1.0,  1.0, 1.0   # sağ üst
    ], dtype=np.float32)

    indices = np.array([
        0, 1, 2,
        0, 2, 3
    ], dtype=np.uint32)

    # VAO, VBO, EBO oluştur
    VAO = glGenVertexArrays(1)
    VBO = glGenBuffers(1)
    EBO = glGenBuffers(1)

    glBindVertexArray(VAO)

    glBindBuffer(GL_ARRAY_BUFFER, VBO)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, EBO)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    # position attribute
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * vertices.itemsize, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    # texCoords attribute
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * vertices.itemsize, ctypes.c_void_p(2 * vertices.itemsize))
    glEnableVertexAttribArray(1)

    glBindVertexArray(0)

    # Ana döngü
    while not glfw.window_should_close(window):
        glfw.poll_events()

        # Ekranı temizle
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)

        # Texture bağla ve çiz
        glUseProgram(shader_program)
        glBindTexture(GL_TEXTURE_2D, texture)
        glBindVertexArray(VAO)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
        glBindTexture(GL_TEXTURE_2D, 0)

        glfw.swap_buffers(window)

    # Temizlik
    glDeleteVertexArrays(1, [VAO])
    glDeleteBuffers(1, [VBO])
    glDeleteBuffers(1, [EBO])
    glDeleteProgram(shader_program)
    glDeleteTextures([texture])

    glfw.terminate()

if __name__ == "__main__":
    main()
