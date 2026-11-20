use std::sync::{atomic::Ordering, OnceLock};

use objc2::{
    class, msg_send,
    rc::Retained,
    runtime::{AnyObject, ClassBuilder, Sel},
    sel,
};
use tauri::{AppHandle, Manager};

use super::{confirm_quit, QuitState};

static APP: OnceLock<AppHandle> = OnceLock::new();

extern "C" fn should_terminate(
    _delegate: *mut AnyObject,
    _selector: Sel,
    _sender: *mut AnyObject,
) -> usize {
    let Some(app) = APP.get() else { return 1 };
    if app.state::<QuitState>().confirmed.load(Ordering::Relaxed) {
        return 1; // NSTerminateNow
    }
    let handle = app.clone();
    let _ = app.run_on_main_thread(move || confirm_quit(&handle));
    0 // NSTerminateCancel. The dialog can subsequently request a Tauri exit.
}

pub fn install(app: &AppHandle) -> Result<(), String> {
    // Tauri has initialized AppKit on the main thread before calling setup.
    let application: Retained<AnyObject> =
        unsafe { msg_send![class!(NSApplication), sharedApplication] };
    let delegate: Option<Retained<AnyObject>> = unsafe { msg_send![&*application, delegate] };
    let delegate = delegate.ok_or("AppKit application delegate is missing")?;
    let mut builder = ClassBuilder::new(c"NeuroDailyApplicationDelegate", delegate.class())
        .ok_or("Could not register the NeuroDaily application delegate")?;
    APP.set(app.clone())
        .map_err(|_| "NeuroDaily quit handler is already installed")?;

    // The subclass has the same instance layout as Tao's original delegate
    // and inherits all its callbacks. Reinstall it to refresh AppKit's flags.
    unsafe {
        builder.add_method(
            sel!(applicationShouldTerminate:),
            should_terminate as extern "C" fn(*mut AnyObject, Sel, *mut AnyObject) -> usize,
        );
        AnyObject::set_class(&delegate, builder.register());
        let _: () = msg_send![&*application, setDelegate: None::<&AnyObject>];
        let _: () = msg_send![&*application, setDelegate: Some(&*delegate)];
    }
    Ok(())
}
