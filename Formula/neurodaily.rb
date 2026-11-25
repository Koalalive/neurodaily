class Neurodaily < Formula
  desc "Research digest and scheduled literature tracking in your browser"
  homepage "https://github.com/Koalalive/neurodaily"
  url "https://github.com/Koalalive/neurodaily.git", using: :git, tag: "cli-v1.0.11"
  version "1.0.11"
  license "Apache-2.0"

  depends_on :macos
  depends_on "python@3.13"

  # Hash-pinned public wheels for the macOS Python 3.13 runtime. Homebrew
  # fetches them before the install sandbox starts, then pip installs offline.

  resource "aiosqlite" do
    url "https://files.pythonhosted.org/packages/00/b7/e3bf5133d697a08128598c8d0abc5e16377b51465a33756de24fa7dee953/aiosqlite-0.22.1-py3-none-any.whl"
    sha256 "21c002eb13823fad740196c5a2e9d8e62f6243bd9e7e4a1f87fb5e44ecb4fceb"
  end

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
    url "https://files.pythonhosted.org/packages/6d/39/5eec3296860b94ac20bb8ed807725b88f6adfab3f343df592afd975f5f86/certifi-2026.11.20-py3-none-any.whl"
    sha256 "7422df25243767b9877031a2248cb14d09ddac9beee846f4cef3d5c9191d488f"
  end

  resource "charset-normalizer" do
    url "https://files.pythonhosted.org/packages/75/59/47eca4000f8367014c2e1be786aa82bd8702120f24749853e6297eb8217b/charset_normalizer-3.5.3-cp313-cp313-macosx_10_13_universal2.whl"
    sha256 "499e4bbeb1e79b14756311a1d12cb88112f244423e152d80981d9bcaff3279fa"
  end

  resource "click" do
    url "https://files.pythonhosted.org/packages/fb/e2/79c688af8b210d232694e31e59da9f6ec747bae31c3f5946e4e9b98860d5/click-8.4.2-py3-none-any.whl"
    sha256 "e6f9f66136c816745b9d65817da91d61d957fb16e02e4dcd0552553c5a197b76"
  end

  resource "distro" do
    url "https://files.pythonhosted.org/packages/12/b3/231ffd4ab1fc9d679809f356cebee130ac7daa00d6d6f3206dd4fd137e9e/distro-1.9.0-py3-none-any.whl"
    sha256 "7bffd925d65168f85027d8da9af6bddab658135b840670a223589bc0c8ef02b2"
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

  resource "httpcore2" do
    url "https://files.pythonhosted.org/packages/2a/e8/009c347feac27f8960605aa98d55ed263b5870dd4fd80b82fd1d00d5716c/httpcore2-2.16.2-py3-none-any.whl"
    sha256 "16051ae2a42f776007543f32de9349a317b23d2cbb4e1456b4bac0e88b87419a"
  end

  resource "httpx" do
    url "https://files.pythonhosted.org/packages/2a/39/e50c7c3a983047577ee07d2a9e53faf5a69493943ec3f6a384bdc792deb2/httpx-0.28.1-py3-none-any.whl"
    sha256 "d909fcccc110f8c7faf814ca82a9a4d816bc5a6dbfea25d6591d6985b8ba59ad"
  end

  resource "httpx2" do
    url "https://files.pythonhosted.org/packages/77/de/8c4306a3d6aa2495111986addf33a9e561eff4c47552e4c4b9251160d0ad/httpx2-2.16.2-py3-none-any.whl"
    sha256 "f05c13aade4c45dbf1c9060647a1058f0acad62398fad96e741269edb33d46f5"
  end

  resource "idna" do
    url "https://files.pythonhosted.org/packages/57/b0/0e52c878c53f245edd3a11020f20979b3f490f245af532c7cae3027754b5/idna-3.19-py3-none-any.whl"
    sha256 "815e7be7a7806d54abb586dc943addc79e8b2ee16915059658cbeff4b1b43bf4"
  end

  resource "jinja2" do
    url "https://files.pythonhosted.org/packages/62/a1/3d680cbfd5f4b8f15abc1d571870c5fc3e594bb582bc3b64ea099db13e56/jinja2-3.1.6-py3-none-any.whl"
    sha256 "85ece4451f492d0c13c5dd7c13a64681a86afae63a5f347908daf103ce6d2f67"
  end

  resource "jsonpatch" do
    url "https://files.pythonhosted.org/packages/76/79/524d5f481ffd5095dd8fdf273bc410214d1a2bb19e6c9a3f379071f1cfc4/jsonpatch-1.48-py3-none-any.whl"
    sha256 "389f25f006940b7bc939c33ca0f6cf8875527dc70599520652a269040ce40b63"
  end

  resource "jsonpointer" do
    url "https://files.pythonhosted.org/packages/72/07/3c953fceee478798f6bdf7b39e0da0793f437e8b5f9e9e1360fba32fb25c/jsonpointer-3.12-py3-none-any.whl"
    sha256 "89f391335ee2719ae72149e1bf30a4d4c7c5d92f15a3f53faa8d20cc7c6c7f19"
  end

  resource "langchain-core" do
    url "https://files.pythonhosted.org/packages/16/6d/35b048329e70492ca0d7561431627ac3b7da1a2dedc99870ca188902529c/langchain_core-1.8.4-py3-none-any.whl"
    sha256 "5755dee8f8b0c709cd22436dea3689c74a3f6e9dc4251590797dcd66bcd1ef67"
  end

  resource "langchain-protocol" do
    url "https://files.pythonhosted.org/packages/71/0a/e96b6ca3b5a7d91af31fd82aee42e65beb6bbe884587e27df5460feee486/langchain_protocol-0.0.22-py3-none-any.whl"
    sha256 "d264998a507b735320c15a7b366051cbf41e21f771bea1b03a911f2c58af02e7"
  end

  resource "langgraph" do
    url "https://files.pythonhosted.org/packages/2d/67/087148694ea5daeb4ebdbf6c02ad642fff0c48ed7c0a189a9fe5e980f221/langgraph-1.2.24-py3-none-any.whl"
    sha256 "312f9a75c1aa0dde5571da32c5c24b891e726fa9781b835b956ec6d9746fa943"
  end

  resource "langgraph-checkpoint" do
    url "https://files.pythonhosted.org/packages/d5/f1/c84ac1431857640bfb9ea811a58ab5b9c040da3842fd1bcf080655184db0/langgraph_checkpoint-4.3.2-py3-none-any.whl"
    sha256 "60e02eb2c2eefc4c22fb1549f1c90b85ce9617377604596c5f34fbd6af0bd6e9"
  end

  resource "langgraph-checkpoint-sqlite" do
    url "https://files.pythonhosted.org/packages/68/e7/574aee0a314fa1c72e62cef2cc22c4f97655a2a18c4031de08d903841b14/langgraph_checkpoint_sqlite-3.1.3-py3-none-any.whl"
    sha256 "7ef55348754b8415e9b2bd2a9d6a385a2246c667a57ad34a591d4ab884a4b1a0"
  end

  resource "langgraph-prebuilt" do
    url "https://files.pythonhosted.org/packages/bc/f3/f1d3426c239dc7eca37e1e49586f7559cc224d3a12933e22e0070a4e8e13/langgraph_prebuilt-1.1.3-py3-none-any.whl"
    sha256 "7b55eb1c2004348b73b9af9e2f81e5f3eda47dcf13d885ccb4195538426c55ce"
  end

  resource "langgraph-sdk" do
    url "https://files.pythonhosted.org/packages/14/f1/3db4776fb3673dbae57b0ad2e9f14d9a2c44bde8932df7df0f7671572ed3/langgraph_sdk-0.4.14-py3-none-any.whl"
    sha256 "d47a6755890ae537aa80613a3138680ac77f5d256a2d3953af95a96328e6964d"
  end

  resource "langsmith" do
    url "https://files.pythonhosted.org/packages/63/79/b2b50b0a6c6ac21c85411d4c5f02e27a5ea965c73ec2836011930d28e65b/langsmith-0.16.1-py3-none-any.whl"
    sha256 "6d7ca07f254839309b6f797062271f5447c25112eda0cec9a0e7606eef77d5ee"
  end

  resource "orjson" do
    url "https://files.pythonhosted.org/packages/a9/56/f8ad2546150168858c16915c452b00eecb79597597524d1ad6ae14ad4eab/orjson-3.13.0-cp313-cp313-macosx_10_15_x86_64.macosx_11_0_arm64.macosx_10_15_universal2.whl"
    sha256 "64e8f345048d988c8b68d3882e5d41028fca1219a9939b32e4a77be34c8ae8e3"
  end

  resource "ormsgpack" do
    url "https://files.pythonhosted.org/packages/be/2b/fff475b90df358a4b348745a870ae408fb954c8afa4dfbcba9b5b3ccba0a/ormsgpack-1.13.1-cp313-cp313-macosx_10_12_universal2.macosx_10_12_x86_64.macosx_11_0_arm64.whl"
    sha256 "236218c74c56e8e3b4acfeecb391a7b34299563d764f2f40ce8cf1f699ff15f1"
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

  resource "requests" do
    url "https://files.pythonhosted.org/packages/a0/f4/c67b0b3f1b9245e8d266f0f112c500d50e5b4e83cb6f3b71b6528104182a/requests-2.34.2-py3-none-any.whl"
    sha256 "2a0d60c172f83ac6ab31e4554906c0f3b3588d37b5cb939b1c061f4907e278e0"
  end

  resource "requests-toolbelt" do
    url "https://files.pythonhosted.org/packages/3f/51/d4db610ef29373b879047326cbf6fa98b6c1969d6f6dc423279de2b1be2c/requests_toolbelt-1.0.0-py2.py3-none-any.whl"
    sha256 "cccfdd665f0a24fcf4726e690f65639d272bb0637b9b92dfd91a5568ccf6bd06"
  end

  resource "setuptools" do
    url "https://files.pythonhosted.org/packages/95/9c/c510029fc6ef33a6275cd2c5d3cecd6613dfd6aa401d57c54f1c18852ccf/setuptools-84.0.0-py3-none-any.whl"
    sha256 "51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670"
  end

  resource "six" do
    url "https://files.pythonhosted.org/packages/b7/ce/149a00dd41f10bc29e5921b496af8b574d8413afcd5e30dfa0ed46c2cc5e/six-1.17.0-py2.py3-none-any.whl"
    sha256 "4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274"
  end

  resource "sniffio" do
    url "https://files.pythonhosted.org/packages/e9/44/75a9c9421471a6c4805dbf2356f7c181a29c1879239abab1ea2cc8f38b40/sniffio-1.3.1-py3-none-any.whl"
    sha256 "2f6da418d1f1e0fddd844478f41680e794e6051915791a034ff65e5f100525a2"
  end

  resource "soupsieve" do
    url "https://files.pythonhosted.org/packages/eb/dc/ad025c1ee131eba60c69f4dd5779b18fcf1e6b21a343e2162a84d5d133c7/soupsieve-2.9.2-py3-none-any.whl"
    sha256 "8089a26fd974ca7a1f30276d3d8492ab266ab15af581642dfe8aa162e0c1c823"
  end

  resource "starlette" do
    url "https://files.pythonhosted.org/packages/c8/cb/6a6a47d5b464bd08695d254f3da6e7986cc70c9fa5d778eda57538edfe56/starlette-1.6.0-py3-none-any.whl"
    sha256 "a86dd39d14bb45f85a3d18525215a9ef0cfd1f192ac793220e72598c90335f0c"
  end

  resource "tenacity" do
    url "https://files.pythonhosted.org/packages/d6/26/1ff2b0721ac66a3ec5b1402b333110b352ab0a8724052ac279a7b82d40c4/tenacity-9.2.1-py3-none-any.whl"
    sha256 "9e56f17539296baab7beabb08b92f6ee3d7be92d8be72d763360677c2ad6580e"
  end

  resource "truststore" do
    url "https://files.pythonhosted.org/packages/51/e9/3a7820be2bb0fe53b6bc9c3be26d3d1158004e4c3ab953aa6840b955b1e9/truststore-0.10.5-py3-none-any.whl"
    sha256 "9aaaedaefaf06d8b206278cf8b5012bc897f485a874503501e12d776df78951c"
  end

  resource "typing-extensions" do
    url "https://files.pythonhosted.org/packages/49/d3/b8441a820a491ddfc024b0b0cf0393375b75ea13866d9c66727e54c2fc80/typing_extensions-4.16.0-py3-none-any.whl"
    sha256 "481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8"
  end

  resource "typing-inspection" do
    url "https://files.pythonhosted.org/packages/67/81/4add07e5172b7ac40d8ed5ff580409a7801a4fe26d529bdd915401dabfbe/typing_inspection-0.4.4-py3-none-any.whl"
    sha256 "65b8397ba37ccbce054456aaccddfc91e6e3083c92824df348d96ca832f3f147"
  end

  resource "urllib3" do
    url "https://files.pythonhosted.org/packages/92/9d/c4e665119135114480843e7ab388fa94d8480650450e6f8e26b70d323a4c/urllib3-2.8.0-py3-none-any.whl"
    sha256 "0cf3cae568d36aa9576b28dfb35f11328f1cb974ca7647d9475ebb86c75ac6e3"
  end

  resource "uuid-utils" do
    url "https://files.pythonhosted.org/packages/fa/ce/78f9d79c820b8afc9b0498b0a5f5ef87ea970a19cc382127087f36cd4839/uuid_utils-0.19.0-cp310-abi3-macosx_10_12_x86_64.macosx_11_0_arm64.macosx_10_12_universal2.whl"
    sha256 "84929d8c594381c6f1444afa2a25cce9ff7edac99d35e071ebc48275bae83730"
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

    resource "sqlite-vec" do
      url "https://files.pythonhosted.org/packages/a4/3d/3677e0cd2f92e5ebc43cd29fbf565b75582bff1ccfa0b8327c7508e1084f/sqlite_vec-0.1.9-py3-none-macosx_11_0_arm64.whl"
      sha256 "1d52e30513bae4cc9778ddbf6145610434081be4c3afe57cd877893bad9f6b6c"
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

    resource "xxhash" do
      url "https://files.pythonhosted.org/packages/5a/7d/1d7779bdf72dbb5178d4237f9f8dd26cc47013738013f20a1270ca6ee4a4/xxhash-4.1.0-cp313-cp313-macosx_11_0_arm64.whl"
      sha256 "01b051e221fface8991b545aea1ef6172cbfe4a1e15f631995d6f7f695377419"
    end

    resource "zstandard" do
      url "https://files.pythonhosted.org/packages/3f/06/9ae96a3e5dcfd119377ba33d4c42a7d89da1efabd5cb3e366b156c45ff4d/zstandard-0.25.0-cp313-cp313-macosx_11_0_arm64.whl"
      sha256 "a1a4ae2dec3993a32247995bdfe367fc3266da832d82f8438c8570f989753de1"
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

    resource "sqlite-vec" do
      url "https://files.pythonhosted.org/packages/68/85/9fad0045d8e7c8df3e0fa5a56c630e8e15ad6e5ca2e6106fceb666aa6638/sqlite_vec-0.1.9-py3-none-macosx_10_6_x86_64.whl"
      sha256 "1b62a7f0a060d9475575d4e599bbf94a13d85af896bc1ce86ee80d1b5b48e5fb"
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

    resource "xxhash" do
      url "https://files.pythonhosted.org/packages/17/0f/1dfee11ef6fa0a984c5ce4a1da3d778a7fcbeea436ebcad45918a69f2c68/xxhash-4.1.0-cp313-cp313-macosx_10_13_x86_64.whl"
      sha256 "676844aad46b4452c7ca2c182a8f388cb8e8ca86fc9e7aaca20455b732adaa57"
    end

    resource "zstandard" do
      url "https://files.pythonhosted.org/packages/35/0b/8df9c4ad06af91d39e94fa96cc010a24ac4ef1378d3efab9223cc8593d40/zstandard-0.25.0-cp313-cp313-macosx_10_13_x86_64.whl"
      sha256 "ec996f12524f88e151c339688c3897194821d7f03081ab35d31d1e12ec975e94"
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
