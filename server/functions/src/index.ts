import * as functions from "firebase-functions";
import * as admin from "firebase-admin";
import { Request, Response } from "express";

admin.initializeApp();

export const occupancyApi = functions
  .https.onRequest(async (req: Request, res: Response) => {
    if (req.method !== "GET") {
      res.status(405).send("Method Not Allowed");
      return;
    }

    try {
      const db = admin.firestore();

      const occupancyEventsRef = db
        .collection("users")
        .doc("test")
        .collection("occupancy_events");

      const snap = await occupancyEventsRef
        .orderBy("captured_at", "desc")
        .limit(1)
        .get();

      if (snap.empty) {
        res.status(404).send("No occupancy event found");
        return;
      }

      const data = snap.docs[0].data() as {
        captured_at: string;
        chairs_num: number;
        persons_num: number;
        occupancy_rate: number;
        occupied_chairs_num: number;
      };

      res.json({
        captured_at: new Date(data.captured_at).toISOString(),
        chairs_num: data.chairs_num,
        persons_num: data.persons_num,
        occupancy_rate: data.occupancy_rate,
        occupied_chairs_num: data.occupied_chairs_num,
      });
    } catch (e) {
      console.error(e);
      res.status(500).send("Internal Server Error");
    }
  });
