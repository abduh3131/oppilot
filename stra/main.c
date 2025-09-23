#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <math.h>

#include <OpenNI.h>      /* C API header is OniCAPI.h, but OpenNI.h includes it safely for C */
#include <OniCAPI.h>

/* Helpers to check OpenNI status */
static void check(oniStatus st, const char* where) {
    if (st != ONI_STATUS_OK) {
        fprintf(stderr, "[ERROR] %s: %s\n", where, oniGetExtendedError());
        exit(1);
    }
}

int main(void) {
    oniStatus st;

    /* 1) Init */
    st = oniInitialize(ONI_API_VERSION);
    check(st, "oniInitialize");

    /* 2) Open first available device */
    OniDeviceHandle device = NULL;
    st = oniDeviceOpen(NULL, &device); /* NULL = first device */
    check(st, "oniDeviceOpen");

    /* 3) Create depth stream */
    OniStreamHandle depth = NULL;
    st = oniDeviceCreateStream(device, ONI_SENSOR_DEPTH, &depth);
    check(st, "oniDeviceCreateStream(DEPTH)");

    /* 4) Configure video mode (optional; try 640x480@30) */
    OniVideoMode mode;
    mode.pixelFormat = ONI_PIXEL_FORMAT_DEPTH_1_MM; /* depth in millimeters */
    mode.resolutionX = 640;
    mode.resolutionY = 480;
    mode.fps         = 30;

    st = oniStreamSetVideoMode(depth, &mode);
    if (st != ONI_STATUS_OK) {
        fprintf(stderr, "[WARN] Failed to set 640x480@30; using device default. (%s)\n", oniGetExtendedError());
    }

    /* 5) Start stream */
    st = oniStreamStart(depth);
    check(st, "oniStreamStart(depth)");

    printf("Depth stream started. Press Ctrl+C to stop.\n");

    /* 6) Main loop: read frames and compute distances */
    OniFrame* frame = NULL;

    /* For FPS estimate */
    uint64_t frames = 0;
    uint64_t t0 = oniGetTimeStamp(); /* microseconds */
    double   lastPrint = 0.0;

    while (1) {
        st = oniStreamReadFrame(depth, &frame);
        if (st != ONI_STATUS_OK || !frame) {
            fprintf(stderr, "[WARN] Failed to read frame: %s\n", oniGetExtendedError());
            continue;
        }

        /* Access depth data */
        const OniDepthPixel* depthData = (const OniDepthPixel*)frame->data;
        int w = frame->width;
        int h = frame->height;

        /* Center pixel distance (mm) */
        int cx = w / 2;
        int cy = h / 2;
        OniDepthPixel center_mm = depthData[cy * w + cx];

        /* Find nearest non-zero pixel in a coarse scan (speed-friendly) */
        OniDepthPixel nearest_mm = 0; /* 0 = no data */
        for (int y = 0; y < h; y += 4) {
            const OniDepthPixel* row = depthData + y * w;
            for (int x = 0; x < w; x += 4) {
                OniDepthPixel d = row[x];
                if (d != 0 && (nearest_mm == 0 || d < nearest_mm)) {
                    nearest_mm = d;
                }
            }
        }

        /* Convert to meters */
        double center_m  = (center_mm > 0) ? center_mm / 1000.0 : NAN;
        double nearest_m = (nearest_mm > 0) ? nearest_mm / 1000.0 : NAN;

        /* FPS update */
        frames++;
        uint64_t t1 = oniGetTimeStamp();
        double elapsed_s = (t1 - t0) / 1000000.0;
        double fps = (elapsed_s > 0.0) ? frames / elapsed_s : 0.0;

        /* Print at ~10 Hz (to keep console readable) */
        if (elapsed_s - lastPrint >= 0.1) {
            if (!isnan(center_m))
                printf("Center: %.3f m  ", center_m);
            else
                printf("Center: N/A      ");

            if (!isnan(nearest_m))
                printf("Nearest: %.3f m  ", nearest_m);
            else
                printf("Nearest: N/A     ");

            printf("| %dx%d @ %.1f FPS\r", w, h, fps);
            fflush(stdout);
            lastPrint = elapsed_s;
        }

        oniFrameRelease(frame);
    }

    /* 7) Cleanup (unreached in this simple loop) */
    oniStreamStop(depth);
    oniStreamDestroy(depth);
    oniDeviceClose(device);
    oniShutdown();
    return 0;
}
