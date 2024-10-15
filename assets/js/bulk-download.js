function urlToPromise(url) {
    return new Promise(function (resolve, reject) {
        JSZipUtils.getBinaryContent(url, function (err, data) {
            if (err) {
                reject(err);
            } else {
                resolve(data);
            }
        });
    });
}

function get_url_extension(url) {
    return url.split(/[#?]/)[0].split('.').pop().trim();
}

function getFileRecords() {
    let files = [];
    $('input[name*="EditRecord"][type="file"]').each(function () {
        const $this = $(this).parent().children('a');
        if ($this.text() != ''){
            var fileRec = {};
            fileRec.filename = $this.text();
            fileRec.url = $this.attr('href');;
            fileRec.ext = get_url_extension(fileRec.filename);
            files.push(fileRec);
        }

    });
    return files;
}

async function generateZip() {
    const files = await getFileRecords()
    const zip = new JSZip();
    await Promise.all(
        files.map(async (fileRec) => {
            zip.file(fileRec.filename, urlToPromise(fileRec.url), {
                binary: true
            });
        })
    )
    return zip;
}

async function run(filename) {
    const zip = await generateZip();
    // when everything has been downloaded, we can trigger the dl
    return zip.generateAsync({
            type: "blob",
            compression: "DEFLATE"
        }, function updateCallback(metadata) {
            let msg = "progression : " + metadata.percent.toFixed(2) + " %";
            if (metadata.currentFile) {
                msg += ", current file = " + metadata.currentFile;
            }
        })
        .then(function callback(blob) {
            saveAs(blob, filename + ".zip");
        }, function (e) {
            console.log(e);
        });
}

document.addEventListener('DataPageReady', function (event) {
    if (event.detail.appKey == 'caf260008b9d7c9e44bc43348bd1') {
        $("#demo").on("click", function () {
            const filename = $('div[data-cb-cell-name*="Calculated_Field_1"]').next();
            run(filename.find('span').text());
            return false;
        });
    }
});
