class Neurodaily < Formula
  desc "Research digest and scheduled literature tracking in your browser"
  homepage "https://github.com/Koalalive/neurodaily"
  url "https://github.com/Koalalive/neurodaily.git", using: :git, tag: "cli-v1.0.8"
  version "1.0.8"
  license "Apache-2.0"

  depends_on :macos
  depends_on "python@3.13"

  # Hash-pinned public wheels for the macOS Python 3.13 runtime. Homebrew
  # fetches them before the install sandbox starts, then pip installs offline.

  resource "annotated-doc" do
    url "https://files.pythonhosted.org/packages/3e/30/e900b21425a860e195f32e37657aa1f7c7f2b1bfb26f03ca209b90933c06/annotated_doc-0.0.5-py3-none-any.whl"
    sha256 "117bac03a25ede5df5440e855b32d556049ca169ead221505badf432fed4b101"
  end

  resource "annotated-types" do
    url "https://files.pythonhosted.org/packages/99/91/8acff4f5e50511b911bbccb72b8628a49c68ce14148cd9f6431094859a90/annotated_types-0.8.0-py3-none-any.whl"
    sha256 "f072f4d804ea359e4eaf198b1af7a8b0943881a87f31bb764f8bf219bb9419e0"
  end

  resource "anyio" do
    url "https://files.pythonhosted.org/packages/da/35/f2287558c17e29fafc8ef3daf819bb9834061cfa43bff8014f7df7f63bdc/anyio-4.14.2-py3-none-any.whl"
    sha256 "9f505dda5ac9f0c8309b5e8bd445a8c2bf7246f3ce950121e45ea15bc41d1494"
  end

  resource "beautifulsoup4" do
    url "https://files.pythonhosted.org/packages/88/c6/92fcd42f1ba33e1184263f25bfabf3d27c383410470f169e4b8163bf9c17/beautifulsoup4-4.15.0-py3-none-any.whl"
    sha256 "d6f88de62e1d4e38ecb1077eb9724cd0eff29d2a08ca16a401e9b9e93f117cf9"
  end

  resource "certifi" do
    url "https://files.pythonhosted.org/packages/0b/a7/71ac2cff56fec219ed242bb11b8efb69fcc4bec75db06fb7bfe35de520e6/certifi-2026.7.22-py3-none-any.whl"
    sha256 "62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775"
  end

  resource "click" do
    url "https://files.pythonhosted.org/packages/fb/e2/79c688af8b210d232694e31e59da9f6ec747bae31c3f5946e4e9b98860d5/click-8.4.2-py3-none-any.whl"
    sha256 "e6f9f66136c816745b9d65817da91d61d957fb16e02e4dcd0552553c5a197b76"
  end

  resource "fastapi" do
    url "https://files.pythonhosted.org/packages/cb/03/10388a42375ee7e4ac9b94eb2c5c569c8b5795e377e701c9ac3ad63de890/fastapi-0.141.1-py3-none-any.whl"
    sha256 "bfb91aa2d334c61cb35ba9a116fc123b3d3df31640b801cf57a7a78ec3f603b3"
  end

  resource "feedparser" do
    url "https://files.pythonhosted.org/packages/7f/61/f04912e63702e73fb2a378f9c0a1ad9eb17a334a11a6b3fe1daa593903c2/feedparser-6.0.14-py3-none-any.whl"
    sha256 "e35e3f760151b0c3b22cac9684155cae186a233e16c49bcbc6c49e91e3131137"
  end

  resource "feedparser-sgmllib" do
    url "https://files.pythonhosted.org/packages/85/a0/79a31f898092e145bd66e2b338fb0656979acb2bbbcae8220940fbfcd820/feedparser_sgmllib-2.1.0-py3-none-any.whl"
    sha256 "2cab2d43b95a954f920f18aebce7a4dbbb3f539780b127e2aa114f579821e01d"
  end

  resource "h11" do
    url "https://files.pythonhosted.org/packages/04/4b/29cac41a4d98d144bf5f6d33995617b185d14b22401f75ca86f384e87ff1/h11-0.16.0-py3-none-any.whl"
    sha256 "63cf8bbe7522de3bf65932fda1d9c2772064ffb3dae62d55932da54b31cb6c86"
  end

  resource "httpcore" do
    url "https://files.pythonhosted.org/packages/7e/f5/f66802a942d491edb555dd61e3a9961140fd64c90bce1eafd741609d334d/httpcore-1.0.9-py3-none-any.whl"
    sha256 "2d400746a40668fc9dec9810239072b40b4484b640a8c38fd654a024c7a1bf55"
  end

  resource "httpx" do
    url "https://files.pythonhosted.org/packages/2a/39/e50c7c3a983047577ee07d2a9e53faf5a69493943ec3f6a384bdc792deb2/httpx-0.28.1-py3-none-any.whl"
    sha256 "d909fcccc110f8c7faf814ca82a9a4d816bc5a6dbfea25d6591d6985b8ba59ad"
  end

  resource "idna" do
    url "https://files.pythonhosted.org/packages/57/b0/0e52c878c53f245edd3a11020f20979b3f490f245af532c7cae3027754b5/idna-3.19-py3-none-any.whl"
    sha256 "815e7be7a7806d54abb586dc943addc79e8b2ee16915059658cbeff4b1b43bf4"
  end

  resource "jinja2" do
    url "https://files.pythonhosted.org/packages/62/a1/3d680cbfd5f4b8f15abc1d571870c5fc3e594bb582bc3b64ea099db13e56/jinja2-3.1.6-py3-none-any.whl"
    sha256 "85ece4451f492d0c13c5dd7c13a64681a86afae63a5f347908daf103ce6d2f67"
  end

  resource "packaging" do
    url "https://files.pythonhosted.org/packages/63/34/ba1c580383c9eada3711951fef0795c80b829a078d72188184bcab9dd527/packaging-26.3-py3-none-any.whl"
    sha256 "d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c"
  end

  resource "pip" do
    url "https://files.pythonhosted.org/packages/07/25/ee8c38ae72d66b844ce8eb9711ba905dba21ca1a8a0c960057c41cd23337/pip-26.3-py3-none-any.whl"
    sha256 "f3b60b20ffaadd4415ed7957212a38ac63fa4c5fa375bd0f4a797777940fad13"
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/fd/7b/122376b1fd3c62c1ed9dc80c931ace4844b3c55407b6fb2d199377c9736f/pydantic-2.13.4-py3-none-any.whl"
    sha256 "45a282cde31d808236fd7ea9d919b128653c8b38b393d1c4ab335c62924d9aba"
  end

  resource "python-dateutil" do
    url "https://files.pythonhosted.org/packages/ec/57/56b9bcc3c9c6a792fcbaf139543cee77261f3651ca9da0c93f5c1221264b/python_dateutil-2.9.0.post0-py2.py3-none-any.whl"
    sha256 "a8b2bc7bffae282281c8140a97d3aa9c14da0b136dfe83f850eea9a5f7470427"
  end

  resource "python-dotenv" do
    url "https://files.pythonhosted.org/packages/0d/17/c5c6b53ddc18f297992099b3d9ec16c855c0ccc83263a21fe4d1c625ec6c/python_dotenv-1.2.3-py3-none-any.whl"
    sha256 "904552145e8bfed22162c09dab1c2b9b54fefa7b23ba780f4f26ca0316b0f0d9"
  end

  resource "setuptools" do
    url "https://files.pythonhosted.org/packages/95/9c/c510029fc6ef33a6275cd2c5d3cecd6613dfd6aa401d57c54f1c18852ccf/setuptools-84.0.0-py3-none-any.whl"
    sha256 "51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670"
  end

  resource "six" do
    url "https://files.pythonhosted.org/packages/b7/ce/149a00dd41f10bc29e5921b496af8b574d8413afcd5e30dfa0ed46c2cc5e/six-1.17.0-py2.py3-none-any.whl"
    sha256 "4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274"
  end

  resource "soupsieve" do
    url "https://files.pythonhosted.org/packages/eb/dc/ad025c1ee131eba60c69f4dd5779b18fcf1e6b21a343e2162a84d5d133c7/soupsieve-2.9.2-py3-none-any.whl"
    sha256 "8089a26fd974ca7a1f30276d3d8492ab266ab15af581642dfe8aa162e0c1c823"
  end

  resource "starlette" do
    url "https://files.pythonhosted.org/packages/c8/cb/6a6a47d5b464bd08695d254f3da6e7986cc70c9fa5d778eda57538edfe56/starlette-1.6.0-py3-none-any.whl"
    sha256 "a86dd39d14bb45f85a3d18525215a9ef0cfd1f192ac793220e72598c90335f0c"
  end

  resource "typing-extensions" do
    url "https://files.pythonhosted.org/packages/49/d3/b8441a820a491ddfc024b0b0cf0393375b75ea13866d9c66727e54c2fc80/typing_extensions-4.16.0-py3-none-any.whl"
    sha256 "481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8"
  end

  resource "typing-inspection" do
    url "https://files.pythonhosted.org/packages/67/81/4add07e5172b7ac40d8ed5ff580409a7801a4fe26d529bdd915401dabfbe/typing_inspection-0.4.4-py3-none-any.whl"
    sha256 "65b8397ba37ccbce054456aaccddfc91e6e3083c92824df348d96ca832f3f147"
  end

  resource "uvicorn" do
    url "https://files.pythonhosted.org/packages/f1/79/4a20b54ab0491485ccd8c077db2d39187c7f12b3e15485d38a7be37c81b4/uvicorn-0.52.4-py3-none-any.whl"
    sha256 "f86e41a149d7d05a9969337e3946a9c171c06a5d42680896daaba624aeac8da1"
  end

  resource "wheel" do
    url "https://files.pythonhosted.org/packages/87/22/b76d483683216dde3d67cba61fb2444be8d5be289bf628c13fc0fd90e5f9/wheel-0.46.3-py3-none-any.whl"
    sha256 "4b399d56c9d9338230118d705d9737a2a468ccca63d5e813e2a4fc7815d8bc4d"
  end

  on_arm do
    resource "httptools" do
      url "https://files.pythonhosted.org/packages/2a/0e/0fb14848c19a686c8062ff9067c1a48793e3224b47bc5b201535b6036fce/httptools-0.8.0-cp313-cp313-macosx_11_0_arm64.whl"
      sha256 "2d689918c15a013c65ef52d9fd495d766893ab831a2c8d89f2ac5940a5df847c"
    end

    resource "markupsafe" do
      url "https://files.pythonhosted.org/packages/9c/d9/5f7756922cdd676869eca1c4e3c0cd0df60ed30199ffd775e319089cb3ed/markupsafe-3.0.3-cp313-cp313-macosx_11_0_arm64.whl"
      sha256 "116bb52f642a37c115f517494ea5feb03889e04df47eeff5b130b1808ce7c219"
    end

    resource "pydantic-core" do
      url "https://files.pythonhosted.org/packages/c1/81/4fa520eaffa8bd7d1525e644cd6d39e7d60b1592bc5b516693c7340b50f1/pydantic_core-2.46.4-cp313-cp313-macosx_11_0_arm64.whl"
      sha256 "c94f0688e7b8d0a67abf40e57a7eaaecd17cc9586706a31b76c031f63df052b4"
    end

    resource "pyyaml" do
      url "https://files.pythonhosted.org/packages/b1/16/95309993f1d3748cd644e02e38b75d50cbc0d9561d21f390a76242ce073f/pyyaml-6.0.3-cp313-cp313-macosx_11_0_arm64.whl"
      sha256 "2283a07e2c21a2aa78d9c4442724ec1eb15f5e42a723b99cb3d822d48f5f7ad1"
    end

    resource "uvloop" do
      url "https://files.pythonhosted.org/packages/89/8c/182a2a593195bfd39842ea68ebc084e20c850806117213f5a299dfc513d9/uvloop-0.22.1-cp313-cp313-macosx_10_13_universal2.whl"
      sha256 "561577354eb94200d75aca23fbde86ee11be36b00e52a4eaf8f50fb0c86b7705"
    end

    resource "watchfiles" do
      url "https://files.pythonhosted.org/packages/31/3a/0da302f2307aee316922806ebd5726c542cbd787c938271cf14a074c7daf/watchfiles-1.2.0-cp313-cp313-macosx_11_0_arm64.whl"
      sha256 "7ba0480b9a74af058f43b337e937a451e109295c420916d68ad24e3dc02f5e44"
    end

    resource "websockets" do
      url "https://files.pythonhosted.org/packages/a2/ef/cc994494bf7d97e41833f6ff55c24f535e4d527a10370b9631737e9c2f00/websockets-17.0.1-cp313-cp313-macosx_11_0_arm64.whl"
      sha256 "734d20364dc2cfe03674883cafcf580b6e431c5ce42b476312b9285310230cf9"
    end
  end

  on_intel do
    resource "httptools" do
      url "https://files.pythonhosted.org/packages/5e/e5/8cfcabc5546e8022f168be28bcdaa128a240a0befdd03b59d558b4f18bd6/httptools-0.8.0-cp313-cp313-macosx_10_13_universal2.whl"
      sha256 "614ceea8ea606848bece2338ac03b3ce5324bcb4be8dc7d377ed708012fa4db8"
    end

    resource "markupsafe" do
      url "https://files.pythonhosted.org/packages/38/2f/907b9c7bbba283e68f20259574b13d005c121a0fa4c175f9bed27c4597ff/markupsafe-3.0.3-cp313-cp313-macosx_10_13_x86_64.whl"
      sha256 "e1cf1972137e83c5d4c136c43ced9ac51d0e124706ee1c8aa8532c1287fa8795"
    end

    resource "pydantic-core" do
      url "https://files.pythonhosted.org/packages/51/a2/5d30b469c5267a17b39dec53208222f76a8d351dfac4af661888c5aee77d/pydantic_core-2.46.4-cp313-cp313-macosx_10_12_x86_64.whl"
      sha256 "5d5902252db0d3cedf8d4a1bc68f70eeb430f7e4c7104c8c476753519b423008"
    end

    resource "pyyaml" do
      url "https://files.pythonhosted.org/packages/d1/11/0fd08f8192109f7169db964b5707a2f1e8b745d4e239b784a5a1dd80d1db/pyyaml-6.0.3-cp313-cp313-macosx_10_13_x86_64.whl"
      sha256 "8da9669d359f02c0b91ccc01cac4a67f16afec0dac22c2ad09f46bee0697eba8"
    end

    resource "uvloop" do
      url "https://files.pythonhosted.org/packages/d2/14/e301ee96a6dc95224b6f1162cd3312f6d1217be3907b79173b06785f2fe7/uvloop-0.22.1-cp313-cp313-macosx_10_13_x86_64.whl"
      sha256 "1cdf5192ab3e674ca26da2eada35b288d2fa49fdd0f357a19f0e7c4e7d5077c8"
    end

    resource "watchfiles" do
      url "https://files.pythonhosted.org/packages/d1/4d/70a7feced9f87e2ff26dba42667290f41694fc64646c67261fbb8cab5d5c/watchfiles-1.2.0-cp313-cp313-macosx_10_12_x86_64.whl"
      sha256 "01ea8d66f0693b9b60a6541c8d10263091ca9a9060d242f3c1f3143f9aad2c98"
    end

    resource "websockets" do
      url "https://files.pythonhosted.org/packages/db/99/e1cfaf419bb3b2fcfd6792a846f1d936293132b0b9a56530ced016c83c7b/websockets-17.0.1-cp313-cp313-macosx_10_13_x86_64.whl"
      sha256 "c1c118a6b0e25bfc9a6802075d748fa6321714ffbdf3c88d29d9a0e3c7386c75"
    end
  end

  def install
    wheelhouse = libexec/"wheelhouse"
    wheelhouse.mkpath
    build_wheels = resources.filter_map do |dependency|
      wheel = wheelhouse/File.basename(dependency.url)
      cp dependency.cached_download, wheel
      wheel if %w[packaging setuptools wheel].include?(dependency.name)
    end

    build_venv = buildpath/"build-venv"
    pip = prepare_pip(build_venv)
    system(*pip, "install", "--no-index", "--no-deps", "--no-compile", *build_wheels)
    system(*pip, "wheel", "--no-index", "--no-deps", "--no-build-isolation", "--wheel-dir", wheelhouse, buildpath)

    pkgshare.install "LICENSE", "NOTICE"
    bin.mkpath
    (bin/"neurodaily").write <<~SH
      #!/bin/sh
      if [ -z "${NEURODAILY_HOME+x}" ]; then
        export NEURODAILY_HOME="$HOME/Library/Application Support/NeuroDaily"
      fi
      exec "#{libexec}/venv/bin/neurodaily" "$@"
    SH
    (bin/"neurodaily").chmod(0o755)
  end

  def post_install
    # Keep wheel Mach-O files intact. Homebrew has already finished relocating
    # built files in this keg, and the PyPI wheels use their own loader paths.
    venv = libexec/"venv"
    pip = prepare_pip(venv)
    system(*pip, "install", "--no-index", "--no-deps", "--no-compile", *(libexec/"wheelhouse").glob("*.whl"))
    system(*pip, "check")
  end

  def caveats
    <<~EOS
      Start the local workspace in your browser:
        neurodaily web

      The default URL is http://127.0.0.1:8031/desktop.
      Existing settings and reports are read from ~/Library/Application Support/NeuroDaily.
    EOS
  end

  test do
    ENV["NEURODAILY_HOME"] = (testpath/"neurodaily-home").to_s
    assert_match "--no-open", shell_output("#{bin}/neurodaily web --help")
    system bin/"neurodaily", "demo", "--no-open"
    assert (testpath/"neurodaily-home"/"output").glob("*.html").any?
  end

  private

  def python
    Formula["python@3.13"].opt_bin/"python3.13"
  end

  def prepare_pip(venv)
    system python, "-m", "venv", "--without-pip", venv
    interpreter = venv/"bin/python"
    bootstrap = <<~PY
      import sys
      import sysconfig
      import zipfile

      with zipfile.ZipFile(sys.argv[1]) as wheel:
          wheel.extractall(sysconfig.get_path("purelib"))
    PY
    pip_wheel = libexec/"wheelhouse"/File.basename(resource("pip").url)
    system interpreter, "-I", "-c", bootstrap, pip_wheel
    [interpreter, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "--no-cache-dir"]
  end
end
