importPackage(Packages.com.ti.debug.engine.scripting);
importPackage(Packages.com.ti.ccstudio.scripting.environment);
importPackage(Packages.java.lang);

var ccxml       = arguments[0];
var mssBin      = arguments[1];
var dssBin      = (arguments.length > 2 && arguments[2] != "NONE") ? arguments[2] : null;
var postRunWait = arguments.length > 3 ? parseInt(arguments[3], 10) : 1500;
if (isNaN(postRunWait) || postRunWait < 100) postRunWait = 1500;

var mssCoreName = "Cortex_R5_0";
var dssCoreName = "C66xx_DSP1";

function sleepMs(ms) {
    java.lang.Thread.sleep(ms);
}

function issueNamedReset(session, resetName) {
    var n = session.target.getNumResetTypes();
    for (var i = 0; i < n; i++) {
        var r = session.target.getResetType(i);
        if (String(r.getName()) == resetName) {
            if (r.isAllowed()) {
                print("Issuing " + resetName + "...");
                r.issueReset();
                return true;
            } else {
                print("WARN: " + resetName + " exists but is not allowed");
                return false;
            }
        }
    }
    print("WARN: " + resetName + " not found, available resets:");
    for (var j = 0; j < n; j++) {
        print("  [" + j + "] " + session.target.getResetType(j).getName());
    }
    return false;
}

function resetCore(session, name) {
    print("Connecting to " + name + "...");
    session.target.connect();
    sleepMs(500);

    if (!issueNamedReset(session, "System Reset")) {
        print("Falling back to generic reset for " + name);
        try { session.target.reset(); } catch (e) {
            print("WARN: generic reset failed on " + name + ": " + e);
        }
    }
    sleepMs(2000);

    try { session.target.connect(); } catch (e) {}
    sleepMs(300);

    issueNamedReset(session, "CPU Reset");
    sleepMs(800);
}

function loadAndRun(session, name, binaryPath) {
    if (binaryPath == null) {
        print("Skipping load for " + name + " (no binary)");
        return;
    }
    try { session.target.connect(); } catch (e) {}
    print("Loading " + name + ": " + binaryPath);
    session.memory.loadProgram(binaryPath);
    sleepMs(800);
    print("Running " + name + "...");
    session.target.runAsynch();
    sleepMs(postRunWait);
}

var script      = null;
var debugServer = null;
var mss         = null;
var dss         = null;

try {
    script = ScriptingEnvironment.instance();
    debugServer = script.getServer("DebugServer.1");
    debugServer.setConfig(ccxml);

    mss = debugServer.openSession("*", mssCoreName);
    resetCore(mss, mssCoreName);
    loadAndRun(mss, mssCoreName, mssBin);

    if (dssBin != null && dssBin != "") {
        dss = debugServer.openSession("*", dssCoreName);
        resetCore(dss, dssCoreName);
        loadAndRun(dss, dssCoreName, dssBin);
    }

    print("OK: reset/load/run completed");

} catch (e) {
    java.lang.System.err.println("ERROR: " + e);
    java.lang.System.exit(99);
} finally {
    try { if (dss != null) { dss.target.disconnect(); dss.terminate(); } } catch (e1) {}
    try { if (mss != null) { mss.target.disconnect(); mss.terminate(); } } catch (e2) {}
    try { if (debugServer != null) debugServer.stop(); } catch (e3) {}
}
